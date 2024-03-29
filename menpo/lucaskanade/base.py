import abc
import numpy as np
from scipy.linalg import solve
from menpo.aam.basicfitting import LKFitting


class LucasKanade(object):
    r"""
    An abstract base class for implementations of Lucas-Kanade [1]_
    type algorithms.

    This is to abstract away optimisation specific functionality such as the
    calculation of the Hessian (which could be derived using a number of
    techniques, including Gauss-Newton and Levenberg-Marquardt).

    Parameters
    ----------
    image : :class:`menpo.image.base.Image`
        The image to perform the alignment upon.

        .. note:: Only the image is expected within the base class because
            different algorithms expect different kinds of template
            (image/model)
    residual : :class:`menpo.lucaskanade.residual.Residual`
        The kind of residual to be calculated. This is used to quantify the
        error between the input image and the reference object.
    transform : :class:`menpo.transform.base.AlignableTransform`
        The transformation type used to warp the image in to the appropriate
        reference frame. This is used by the warping function to calculate
        sub-pixel coordinates of the input image in the reference frame.
    warp : function
        A function that takes 3 arguments,
        ``warp(`` :class:`image <menpo.image.base.Image>`,
        :class:`template <menpo.image.base.Image>`,
        :class:`transform <menpo.transform.base.AlignableTransform>` ``)``
        This function is intended to perform sub-pixel interpolation of the
        pixel locations calculated by transforming the given image into the
        reference frame of the template. Appropriate functions are given in
        :doc:`menpo.interpolation`.
    optimisation : ('GN',) | ('LM', float), optional
        The optimisation technique used to calculate the Hessian approximation.
        Note that for 'LM' the float is used to set the update step.

        Default: 'GN'
    update_step : float, optional
        The update step used when performing a Levenberg-Marquardt
        optimisation.

        Default: 0.001
    eps : float, optional
        The convergence value. When calculating the level of convergence, if
        the norm of the delta parameter updates is less than ``eps``, the
        algorithm is considered to have converged.

        Default: 1**-10

    Notes
    -----
    The type of optimisation technique chosen will determine properties such
    as the convergence rate of the algorithm. The supported optimisation
    techniques are detailed below:

    ===== ==================== ===============================================
    type  full name            hessian approximation
    ===== ==================== ===============================================
    'GN'  Gauss-Newton         :math:`\mathbf{J^T J}`
    'LM'  Levenberg-Marquardt  :math:`\mathbf{J^T J + \lambda\, diag(J^T J)}`
    ===== ==================== ===============================================

    Attributes
    ----------
    transform
    parameters
    n_iters

    References
    ----------
    .. [1] Lucas, Bruce D., and Takeo Kanade.
       "An iterative image registration technique with an application to
       stereo vision." IJCAI. Vol. 81. 1981.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, residual, transform,
                 interpolator='scipy', optimisation=('GN',), eps=1**-10):
        # set basic state for all Lucas Kanade algorithms
        self.transform = transform
        self.residual = residual
        self.eps = eps

        # select the optimisation approach and warp function
        self._calculate_delta_p = self._select_optimisation(optimisation)
        self._interpolator = interpolator

    def _select_optimisation(self, optimisation):
        if optimisation[0] == 'GD':
            self.update_step = optimisation[1]
            self.__e_lm = 0
            return self._gradient_descent
        if optimisation[0] == 'GN':
            return self._gauss_newton_update
        elif optimisation[0] == 'GN_lp':
            self.lp = optimisation[1]
            return self._gauss_newton_lp_update
        elif optimisation[0] == 'LM':
            self.update_step = optimisation[1]
            self.__e_lm = 0
            return self._levenberg_marquardt_update
        else:
            raise ValueError('Unknown optimisation string selected. Valid'
                             'options are: GN, GN_lp, LM')

    def _gradient_descent(self, sd_delta_p):
        raise NotImplementedError("Gradient descent optimization not "
                                  "implemented yet")

    def _gauss_newton_update(self, sd_delta_p):
        return solve(self._H, sd_delta_p)

    def _gauss_newton_lp_update(self, sd_delta_p):
        raise NotImplementedError("Gauss-Newton lp-norm optimization not "
                                  "implemented yet")

    def _levenberg_marquardt_update(self, sd_delta_p):
        LM = np.diagflat(np.diagonal(self._H))
        H_lm = self._H + (self.update_step * LM)

        if self.residual.error < self.__e_lm:
            # Bad step, increase step
            self.update_step *= 10
        else:
            # Good step, decrease step
            self.update_step /= 10
            self.__e_lm = self.residual.error

        return solve(H_lm, sd_delta_p)

    def _precompute(self):
        """
        Performs pre-computations related to specific alignment algorithms
        """
        pass

    def align(self, image, parameters, max_iters=20, **kwargs):
        r"""
        Perform an alignment using the Lukas-Kanade framework.

        Parameters
        ----------
        max_iters : int
            The maximum number of iterations that will be used in performing
            the alignment

        Returns
        -------
        transform : :class:`menpo.transform.base.AlignableTransform`
            The final transform that optimally aligns the source to the
            target.
        """
        self.transform.from_vector_inplace(parameters)
        lk_fitting = LKFitting(image, self, parameters=[parameters])
        return self._align(lk_fitting, max_iters=max_iters, **kwargs)

    @abc.abstractmethod
    def _align(self, lk_fitting, **kwargs):
        r"""
        Abstract method to be overridden by subclasses that implements the
        alignment algorithm.
        """
        pass
