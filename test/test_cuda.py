import unittest
import numpy as np
from numpy.fft import fftn, ifftn, fftshift, rfftn, irfftn

try:
    from scipy.misc import ascent
except ImportError:
    def ascent():
        return np.random.randint(0, 255, (512, 512))
from pyvkfft.cuda import VkFFTApp, primes

try:
    import pycuda.autoinit
    import pycuda.driver as cu_drv
    import pycuda.gpuarray as cua
except:
    cua = None


class TestVkFFTCUDA(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.dtype_float_v = [np.float32]
        cls.dtype_complex_v = [np.complex64]

    def test_pycuda(self):
        self.assertTrue(cua is not None, "pycuda is not available")

    @unittest.skipIf(cua is None, "cuda or pycuda is not available")
    def test_c2c(self):
        """
        Test inplace C2C transforms
        """
        for n in [32, 17]:  # test both radix-2 and Bluestein algorithms
            for dims in range(1, 5):
                for ndim0 in range(1, min(dims, 3) + 1):
                    # Setup use of either ndim or axes, also test skipping dimensions
                    ndim_axes = [(ndim0, None)]
                    for i in range(1, 2 ** (ndim0 - 1)):
                        axes = []
                        for ii in range(ndim0):
                            if not (i & 2 ** ii):
                                axes.append(-ii - 1)
                        ndim_axes.append((None, axes))
                    for ndim, axes in ndim_axes:
                        for dtype in self.dtype_complex_v:
                            for norm in [0, 1, "ortho"]:
                                with self.subTest(n=n, dims=dims, ndim=ndim, axes=axes, dtype=dtype, norm=norm):
                                    if dtype == np.complex64:
                                        rtol = 1e-6
                                    else:
                                        rtol = 1e-12
                                    if max(primes(n)) > 13:
                                        rtol *= 4  # Lower accuracy for Bluestein algorithm

                                    d = np.random.uniform(0, 1, [n] * dims).astype(dtype)
                                    # A pure random array may not be a very good test (too random),
                                    # so add a Gaussian
                                    xx = [np.fft.fftshift(np.fft.fftfreq(n))] * dims
                                    v = np.zeros_like(d)
                                    for x in np.meshgrid(*xx, indexing='ij'):
                                        v += x ** 2
                                    d += 10 * np.exp(-v * 2)
                                    n0 = (abs(d) ** 2).sum()
                                    d_gpu = cua.to_gpu(d)
                                    app = VkFFTApp(d.shape, d.dtype, ndim=ndim, norm=norm, axes=axes)
                                    if axes is None:
                                        axes = list(range(dims))[-ndim:]  # For numpy
                                    # base FFT scale for numpy
                                    s = np.sqrt(np.prod([d.shape[i] for i in axes]))

                                    d = fftn(d, axes=axes) / s
                                    d_gpu = app.fft(d_gpu) * app.get_fft_scale()
                                    self.assertTrue(np.allclose(d, d_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))

                                    d = ifftn(d, axes=axes) * s
                                    d_gpu = app.ifft(d_gpu) * app.get_ifft_scale()
                                    self.assertTrue(np.allclose(d, d_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))
                                    n1 = (abs(d_gpu.get()) ** 2).sum()
                                    self.assertTrue(np.isclose(n0, n1, rtol=rtol))

    @unittest.skipIf(cua is None, "cuda or pycuda is not available")
    def test_c2c_outofplace(self):
        """
        Test out-of-place C2C transforms
        """
        for n in [32, 17]:  # test both radix-2 and Bluestein algorithms
            for dims in range(1, 5):
                for ndim0 in range(1, min(dims, 3) + 1):
                    # Setup use of either ndim or axes, also test skipping dimensions
                    ndim_axes = [(ndim0, None)]
                    for i in range(1, 2 ** (ndim0 - 1)):
                        axes = []
                        for ii in range(ndim0):
                            if not (i & 2 ** ii):
                                axes.append(-ii - 1)
                        ndim_axes.append((None, axes))
                    for ndim, axes in ndim_axes:
                        for dtype in self.dtype_complex_v:
                            for norm in [0, 1, "ortho"]:
                                with self.subTest(n=n, dims=dims, ndim=ndim, axes=axes, dtype=dtype, norm=norm):
                                    if dtype == np.complex64:
                                        rtol = 1e-6
                                    else:
                                        rtol = 1e-12
                                    if max(primes(n)) > 13:
                                        rtol *= 4  # Lower accuracy for Bluestein algorithm

                                    d = np.random.uniform(0, 1, [n] * dims).astype(dtype)
                                    # A pure random array may not be a very good test (too random),
                                    # so add a Gaussian
                                    xx = [np.fft.fftshift(np.fft.fftfreq(n))] * dims
                                    v = np.zeros_like(d)
                                    for x in np.meshgrid(*xx, indexing='ij'):
                                        v += x ** 2
                                    d += 10 * np.exp(-v * 2)
                                    n0 = (abs(d) ** 2).sum()
                                    d_gpu = cua.to_gpu(d)
                                    d1_gpu = cua.empty_like(d_gpu)
                                    app = VkFFTApp(d.shape, d.dtype, ndim=ndim, norm=norm, axes=axes, inplace=False)
                                    if axes is None:
                                        axes = list(range(dims))[-ndim:]  # For numpy
                                    # base FFT scale for numpy
                                    s = np.sqrt(np.prod([d.shape[i] for i in axes]))

                                    d = fftn(d, axes=axes) / s
                                    d1_gpu = app.fft(d_gpu, d1_gpu) * app.get_fft_scale()
                                    self.assertTrue(np.allclose(d, d1_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))

                                    d = ifftn(d, axes=axes) * s
                                    d_gpu = app.ifft(d1_gpu, d_gpu) * app.get_ifft_scale()
                                    self.assertTrue(np.allclose(d, d_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))
                                    n1 = (abs(d_gpu.get()) ** 2).sum()
                                    self.assertTrue(np.isclose(n0, n1, rtol=rtol))

    @unittest.skipIf(cua is None, "cuda or pycuda is not available")
    def test_r2c(self):
        """
        Test inplace R2C transforms
        """
        for n in [32, 34]:
            # test both radix-2 and Bluestein algorithms.
            # We need a multiple of 2 for the first axis of an inplace R2C transform
            for dims in range(1, 5):
                for ndim in range(1, min(dims, 3) + 1):
                    for dtype in self.dtype_float_v:
                        for norm in [0, 1, "ortho"]:
                            with self.subTest(n=n, dims=dims, ndim=ndim, dtype=dtype, norm=norm):
                                if dtype == np.float32:
                                    rtol = 1e-6
                                else:
                                    rtol = 1e-12
                                if max(primes(n)) > 13:
                                    rtol *= 4  # Lower accuracy for Bluestein algorithm

                                sh = [n] * dims
                                sh[-1] += 2
                                shc = [n] * dims
                                shc[-1] = n // 2 + 1

                                d = np.random.uniform(0, 1, sh).astype(dtype)
                                # A pure random array may not be a very good test (too random),
                                # so add a Gaussian
                                xx = [np.fft.fftshift(np.fft.fftfreq(nn)) for nn in sh]
                                v = np.zeros_like(d)
                                for x in np.meshgrid(*xx, indexing='ij'):
                                    v += x ** 2
                                d += 10 * np.exp(-v * 2)
                                n0 = (abs(d[..., :-2]) ** 2).sum()
                                d_gpu = cua.to_gpu(d)
                                app = VkFFTApp(d.shape, d.dtype, ndim=ndim, norm=norm, r2c=True)
                                # base FFT scale
                                s = np.sqrt(n ** ndim)

                                d = rfftn(d[..., :-2], axes=list(range(dims))[-ndim:]) / s
                                d_gpu = app.fft(d_gpu) * app.get_fft_scale()
                                self.assertTrue(d_gpu.shape == tuple(shc))

                                if dtype == np.float32:
                                    self.assertTrue(d_gpu.dtype == np.complex64)
                                elif dtype == np.float64:
                                    self.assertTrue(d_gpu.dtype == np.complex128)

                                self.assertTrue(np.allclose(d, d_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))

                                d = irfftn(d, axes=list(range(dims))[-ndim:]) * s
                                d_gpu = app.ifft(d_gpu) * app.get_ifft_scale()
                                self.assertTrue(d_gpu.shape == tuple(sh))

                                self.assertTrue(np.allclose(d, d_gpu.get()[..., :-2], rtol=rtol, atol=abs(d).max() * rtol))
                                n1 = (abs(d_gpu.get()[..., :-2]) ** 2).sum()
                                self.assertTrue(np.isclose(n0, n1, rtol=rtol))

    @unittest.skipIf(cua is None, "cuda or pycuda is not available")
    def test_r2c_outofplace(self):
        """
        Test out-of-place R2C transforms
        """
        for n in [32, 17]:  # test both radix-2 and Bluestein algorithms.
            for dims in range(1, 5):
                for ndim in range(1, min(dims, 3) + 1):
                    for dtype in self.dtype_float_v:
                        for norm in [0, 1, "ortho"]:
                            with self.subTest(n=n, dims=dims, ndim=ndim, dtype=dtype, norm=norm):
                                if dtype == np.float32:
                                    rtol = 1e-6
                                else:
                                    rtol = 1e-12
                                if max(primes(n)) > 13:
                                    rtol *= 4  # Lower accuracy for Bluestein algorithm

                                if dtype == np.float32:
                                    dtype_c = np.complex64
                                elif dtype == np.float64:
                                    dtype_c = np.complex128

                                sh = [n] * dims
                                sh = tuple(sh)
                                shc = [n] * dims
                                shc[-1] = n // 2 + 1
                                shc = tuple(shc)

                                d = np.random.uniform(0, 1, sh).astype(dtype)
                                # A pure random array may not be a very good test (too random),
                                # so add a Gaussian
                                xx = [np.fft.fftshift(np.fft.fftfreq(nn)) for nn in sh]
                                v = np.zeros_like(d)
                                for x in np.meshgrid(*xx, indexing='ij'):
                                    v += x ** 2
                                d += 10 * np.exp(-v * 2)
                                n0 = (abs(d) ** 2).sum()
                                d_gpu = cua.to_gpu(d)
                                d1_gpu = cua.empty(shc, dtype=dtype_c)

                                app = VkFFTApp(d.shape, d.dtype, ndim=ndim, norm=norm, r2c=True, inplace=False)
                                # base FFT scale
                                s = np.sqrt(np.prod(d.shape[-ndim:]))

                                d = rfftn(d, axes=list(range(dims))[-ndim:]) / s
                                d1_gpu = app.fft(d_gpu, d1_gpu) * app.get_fft_scale()
                                self.assertTrue(d1_gpu.shape == tuple(shc))
                                self.assertTrue(d1_gpu.dtype == dtype_c)

                                self.assertTrue(np.allclose(d, d1_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))

                                # The shape of the transformed axes must be supplied for scipy.fft.irfftn
                                axes = list(range(dims))[-ndim:]
                                d = irfftn(d, [sh[i] for i in axes], axes=axes) * s
                                d_gpu = app.ifft(d1_gpu, d_gpu) * app.get_ifft_scale()
                                self.assertTrue(d_gpu.shape == tuple(sh))

                                self.assertTrue(np.allclose(d, d_gpu.get(), rtol=rtol, atol=abs(d).max() * rtol))
                                n1 = (abs(d_gpu.get()) ** 2).sum()
                                self.assertTrue(np.isclose(n0, n1, rtol=rtol))

    def test_streams(self):
        """
        Test multiple FFT in // with different streams.
        :return:
        """
        for dtype in [np.complex64, np.complex128]:
            if dtype == np.complex64:
                rtol = 1e-6
            else:
                rtol = 1e-12
            d = ascent().astype(dtype)
            n_streams = 5
            vd = []
            vapp = []
            for i in range(n_streams):
                vd.append(cua.to_gpu(np.roll(d, i * 7, axis=1)))
                vapp.append(VkFFTApp(d.shape, d.dtype, ndim=2, norm=1, stream=cu_drv.Stream()))

            for i in range(n_streams):
                vapp[i].fft(vd[i])
            for i in range(n_streams):
                dn = fftn(np.roll(d, i * 7, axis=1))
                self.assertTrue(np.allclose(dn, vd[i].get(), rtol=rtol, atol=abs(dn).max() * rtol))

            for i in range(n_streams):
                vapp[i].ifft(vd[i])
            for i in range(n_streams):
                dn = np.roll(d, i * 7, axis=1)
                self.assertTrue(np.allclose(dn, vd[i].get(), rtol=rtol, atol=abs(dn).max() * rtol))


def suite():
    test_suite = unittest.TestSuite()
    load_tests = unittest.defaultTestLoader.loadTestsFromTestCase
    test_suite.addTest(load_tests(TestVkFFTCUDA))
    return test_suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
