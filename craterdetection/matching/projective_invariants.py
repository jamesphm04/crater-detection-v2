import numpy as np
import numpy.linalg as LA

from craterdetection.common.conics import matrix_adjugate, scale_det, crater_representation
from craterdetection.matching.utils import np_swap_columns, is_colinear, is_clockwise, all_clockwise, \
    enhanced_pattern_shifting


class PermutationInvariant:
    """
    Namespace for permutation invariants functions
    """

    @staticmethod
    def F1(x, y, z):
        return x + y + z

    @staticmethod
    def F2(x, y, z):
        return (2 * (x ** 3 + y ** 3 + z ** 3) + 12 * x * y * z - 3 * (
                (x ** 2) * y + (y ** 2) * x + (y ** 2) * z + (z ** 2) * y + (z ** 2) * x + (x ** 2) * z)) / \
               (x ** 2 + y ** 2 + z ** 2 - (x * y + y * z + z * x))

    @staticmethod
    def F3(x, y, z):
        return (-3 * np.sqrt(3) * (x - y) * (y - z) * (z - x)) / (x ** 2 + y ** 2 + z ** 2 - (x * y + y * z + z * x))

    @classmethod
    def F(cls, x, y, z):
        """Three-pair cyclic permutation invariant function.

        Parameters
        ----------
        x, y, z : int or float or np.ndarray
            Values to generate cyclic permutation invariant features for

        Returns
        -------
        np.ndarray
            Array containing cyclic permutation invariants F1, F2, F3

        References
        ----------
        .. [1] Christian, J. A., Derksen, H., & Watkins, R. (2020). Lunar Crater Identification in Digital Images. http://arxiv.org/abs/2009.01228
        """
        return np.array((cls.F1(x, y, z), cls.F2(x, y, z), cls.F3(x, y, z)))

    @staticmethod
    def G1(x1, y1, z1, x2, y2, z2):
        return 1.5 * (x1 * x2 + y1 * y2 + z1 * z2) - 0.5 * (x1 + y1 + z1) * (x2 + y2 + z2)

    @staticmethod
    def G2(x1, y1, z1, x2, y2, z2):
        return (np.sqrt(3) / 2.) * ((x1 * z2 + y1 * x2 + z1 * y2) - (x1 * y2 + y1 * z2 + z1 * x2))

    # TODO: Fix cyclic permutation invariant G
    @classmethod
    def G(cls, x1, y1, z1, x2, y2, z2):
        return np.array((cls.G1(x1, y1, z1, x2, y2, z2), cls.G2(x1, y1, z1, x2, y2, z2)))

    @classmethod
    def G_tilde(cls, x1, y1, z1, x2, y2, z2):
        """

        Parameters
        ----------
        x1, y1, z1 : int or float or np.ndarray
            First set of values to generate cyclic permutation invariant features for
        x2, y2, z2 : int or float or np.ndarray
            Second set of values to generate cyclic permutation invariant features for

        Returns
        -------
        np.ndarray
            Array containing cyclic permutation invariants G1, G2

        References
        ----------
        .. [1] Christian, J. A., Derksen, H., & Watkins, R. (2020). Lunar Crater Identification in Digital Images. http://arxiv.org/abs/2009.01228

        """
        return cls.G(x1, y1, z1, x2, y2, z2) / np.sqrt(np.sqrt(
            (((x1 - y1) ** 2 + (y1 - z1) ** 2 + (z1 - x1) ** 2) * ((x2 - y2) ** 2 + (y2 - z2) ** 2 + (z2 - x2) ** 2))))


class CoplanarInvariants:
    def __init__(self, crater_triads, A_i, A_j, A_k, normalize_det=True):
        """Generates projective invariants [1] assuming craters are coplanar. Input is an array of crater matrices
        such as those generated using L{crater_representation}.

        Parameters
        ----------
        crater_triads : np.ndarray
            Crater triad indices (nx3) for slicing arrays
        A_i : np.ndarray
            Crater representation first crater in triad
        A_j : np.ndarray
            Crater representation second crater in triad
        A_k : np.ndarray
            Crater representation third crater in triad
        normalize_det : bool
            Set to True to normalize matrices to achieve det(A) = 1

        References
        ----------
        .. [1] Christian, J. A., Derksen, H., & Watkins, R. (2020). Lunar Crater Identification in Digital Images. http://arxiv.org/abs/2009.01228
        """

        self.crater_triads = crater_triads
        overlapped_craters = ~np.logical_and.reduce((
            np.isfinite(LA.cond(A_i - A_j)),
            np.isfinite(LA.cond(A_i - A_k)),
            np.isfinite(LA.cond(A_j - A_k))
        ))
        A_i, A_j, A_k = map(lambda craters_: craters_[~overlapped_craters], (A_i, A_j, A_k))
        self.crater_triads = self.crater_triads[~overlapped_craters]

        if normalize_det:
            A_i, A_j, A_k = map(scale_det, (A_i, A_j, A_k))

        self.I_ij, self.I_ji = np.trace(LA.inv(A_i) @ A_j, axis1=-2, axis2=-1), np.trace(LA.inv(A_j) @ A_i, axis1=-2,
                                                                                         axis2=-1)
        self.I_ik, self.I_ki = np.trace(LA.inv(A_i) @ A_k, axis1=-2, axis2=-1), np.trace(LA.inv(A_k) @ A_i, axis1=-2,
                                                                                         axis2=-1)
        self.I_jk, self.I_kj = np.trace(LA.inv(A_j) @ A_k, axis1=-2, axis2=-1), np.trace(LA.inv(A_k) @ A_j, axis1=-2,
                                                                                         axis2=-1)
        self.I_ijk = np.trace((matrix_adjugate(A_j + A_k) - matrix_adjugate(A_j - A_k)) @ A_i, axis1=-2, axis2=-1)

    @classmethod
    def from_detection_conics(cls,
                              A_craters,
                              crater_triads=None
                              ):

        if crater_triads is None:
            n_det = len(A_craters)
            n_comb = int((n_det * (n_det - 1) * (n_det - 2)) / 6)

            crater_triads = np.zeros((n_comb, 3), np.int)
            for it, (i, j, k) in enumerate(enhanced_pattern_shifting(n_det)):
                crater_triads[it] = np.array([i, j, k])



        x_triads, y_triads = x_pix[crater_triads].T, y_pix[crater_triads].T
        clockwise = is_clockwise(x_triads, y_triads)

        crater_triads_cw = crater_triads.copy()
        crater_triads_cw[~clockwise] = np_swap_columns(crater_triads[~clockwise])
        x_triads[:, ~clockwise] = np_swap_columns(x_triads.T[~clockwise]).T
        y_triads[:, ~clockwise] = np_swap_columns(y_triads.T[~clockwise]).T

        if not all_clockwise(x_triads, y_triads):
            line = is_colinear(x_triads, y_triads)
            x_triads = x_triads[:, ~line]
            y_triads = y_triads[:, ~line]
            crater_triads_cw = crater_triads_cw[~line]

            if not all_clockwise(x_triads, y_triads):
                print("Failed to order all triads in clockwise order. Removing ccw triads...")
                clockwise = is_clockwise(x_triads, y_triads)
                x_triads = x_triads[:, clockwise]
                y_triads = y_triads[:, clockwise]
                crater_triads_cw = crater_triads_cw[clockwise]

    @classmethod
    def from_detection(cls,
                       x_pix,
                       y_pix,
                       a_pix,
                       b_pix,
                       psi_pix,
                       convert_to_radians=True,
                       crater_triads=None
                       ):
        """

        Parameters
        ----------
        x_pix, y_pix : np.ndarray
            Crater center positions in image plane
        a_pix, b_pix : np.ndarray
            Crater ellipse axis parameters in image plane
        psi_pix : np.ndarray
            Crater ellipse angle w.r.t. x-direction in image plane
        convert_to_radians : bool
            Whether to convert psi to radians inside method (default: True)
        crater_triads : np.ndarray
            nx3 array of indices for crater triad(s)

        Returns
        -------
        CoplanarInvariants

        """

        if convert_to_radians:
            psi_pix = np.radians(psi_pix)

        A_craters = crater_representation(a_pix, b_pix, psi_pix, x_pix, y_pix)

        return cls.from_detection_conics(A_craters, crater_triads)

    @classmethod
    def match_generator(cls,
                        x_pix,
                        y_pix,
                        a_pix,
                        b_pix,
                        psi_pix,
                        convert_to_radians=True
                        ):
        """ Generator function that yields crater triad and its associated projective invariants [1]. Triads are formed
        using Enhanced Pattern Shifting method [2].

        Parameters
        ----------
        x_pix, y_pix : np.ndarray
            Crater center positions in image plane
        a_pix, b_pix : np.ndarray
            Crater ellipse axis parameters in image plane
        psi_pix : np.ndarray
            Crater ellipse angle w.r.t. x-direction in image plane
        convert_to_radians : bool
            Whether to convert psi to radians inside method (default: True)

        Yields
        ------
        crater_triad : np.ndarray
            Triad indices (1x3)
        CoplanarInvariants
             Associated CoplanarInvariants instance

        References
        ----------
        .. [1] Christian, J. A., Derksen, H., & Watkins, R. (2020). Lunar Crater Identification in Digital Images. http://arxiv.org/abs/2009.01228
        .. [2] Arnas, D., Fialho, M. A. A., & Mortari, D. (2017). Fast and robust kernel generators for star trackers. Acta Astronautica, 134 (August 2016), 291–302. https://doi.org/10.1016/j.actaastro.2017.02.016

        """
        n_det = len(x_pix)
        for i, j, k in enhanced_pattern_shifting(n_det):
            crater_triads = np.array([i, j, k])[None, :]
            yield crater_triads.squeeze(), cls.from_detection(x_pix,
                                                              y_pix,
                                                              a_pix,
                                                              b_pix,
                                                              psi_pix,
                                                              convert_to_radians,
                                                              crater_triads
                                                              )

    def get_pattern(self, permutation_invariant=False):
        """Get matching pattern using either permutation invariant features (eq. 134 from [1]) or raw projective
        invariants (p. 61 from [1]).

        Parameters
        ----------
        permutation_invariant : bool
            Set this to True if permutation_invariants are needed.

        Returns
        -------
        np.ndarray
            Array of features linked to the crater triads generated during initialisation.

        References
        ----------
        .. [1] Christian, J. A., Derksen, H., & Watkins, R. (2020). Lunar Crater Identification in Digital Images. http://arxiv.org/abs/2009.01228
        """

        if permutation_invariant:
            return np.column_stack((
                PermutationInvariant.F(self.I_ij, self.I_jk, self.I_ki).T,
                PermutationInvariant.F1(self.I_ji, self.I_kj, self.I_ik),
                PermutationInvariant.G_tilde(self.I_ij, self.I_jk, self.I_ki, self.I_ji, self.I_kj, self.I_ik).T,
                self.I_ijk
            )).T

        else:
            return np.column_stack((
                self.I_ij,
                self.I_ji,
                self.I_ik,
                self.I_ki,
                self.I_jk,
                self.I_kj,
                self.I_ijk,
            ))

    def __len__(self):
        return len(self.I_ij)
