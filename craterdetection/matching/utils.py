import numpy as np
import numpy.linalg as LA
import networkx as nx


def triad_splice(arr, triads):
    return arr[triads].T


def np_swap_columns(arr):
    arr[:, 0], arr[:, 1] = arr[:, 1], arr[:, 0].copy()
    return arr


def cw_or_ccw(x_triads, y_triads):
    return LA.det(np.moveaxis(np.array([[x_triads[0], y_triads[0], np.ones_like(x_triads[0])],
                                        [x_triads[1], y_triads[1], np.ones_like(x_triads[0])],
                                        [x_triads[2], y_triads[2], np.ones_like(x_triads[0])]]), -1, 0))


def is_colinear(x_triads_, y_triads_):
    return cw_or_ccw(x_triads_, y_triads_) == 0


def is_clockwise(x_triads, y_triads):
    """Returns boolean array which tells whether the three points in 2D plane given by x_triads & y_triads are
    oriented clockwise. https://en.wikipedia.org/wiki/Curve_orientation#Orientation_of_a_simple_polygon

    Parameters
    ----------
    x_triads, y_triads : np.ndarray
        Array of 2D coordinates for triangles in a plane

    Returns
    -------
    np.ndarray
    """
    return cw_or_ccw(x_triads, y_triads) < 0


def all_clockwise(x_triads_, y_triads_):
    return np.logical_and.reduce(is_clockwise(x_triads_, y_triads_))


def cyclic_permutations(it):
    """Returns cyclic permutations for iterable.

    Parameters
    ----------
    it
        Iterable

    Yields
    -------
    Cyclic permutation of it
    """

    yield it
    for k in range(1, len(it)):
        p = it[k:] + it[:k]
        if p == it:
            break
        yield p


# https://stackoverflow.com/questions/1705824/finding-cycle-of-3-nodes-or-triangles-in-a-graph
def get_cliques_by_length(G, length_clique):
    """ Return the list of all cliques in an undirected graph G with length
    equal to length_clique. """
    cliques = []
    for c in nx.enumerate_all_cliques(G):
        if len(c) <= length_clique:
            if len(c) == length_clique:
                cliques.append(c)
        else:
            return cliques
    # return empty list if nothing is found
    return cliques


def latlong2cartesian(lat, long, alt=0, rad=1737.1):
    """
    Calculate Cartesian coordinates from latitude + longitude information
    """
    f = 1. / 825.  # flattening (Moon)
    ls = np.arctan((1 - f) ** 2 * np.tan(lat))  # lambda

    x = rad * np.cos(ls) * np.cos(long) + alt * np.cos(lat) * np.cos(long)
    y = rad * np.cos(ls) * np.sin(long) + alt * np.cos(lat) * np.sin(long)
    z = rad * np.sin(ls) + alt * np.sin(lat)

    return x, y, z


def enhanced_pattern_shifting(n):
    """Generator function returning next crater triad according to Enhanced Pattern Shifting Method [1].

    Parameters
    ----------
    n : int
        Number of detected instances

    Returns
    -------
    i, j, k : Iter

    References
    ----------
    .. [1] Arnas, D., Fialho, M. A. A., & Mortari, D. (2017). Fast and robust kernel generators for star trackers. Acta Astronautica, 134 (August 2016), 291–302. https://doi.org/10.1016/j.actaastro.2017.02.016
    """
    for dj in range(1, n-2):
        for dk in range(1, n-dj-1):
            for ii in range(0, 3):
                for i in range(ii, n-dj-dk, 3):
                    j = i + dj
                    k = j + dk
                    yield i, j, k
