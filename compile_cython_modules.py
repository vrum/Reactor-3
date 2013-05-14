from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [Extension('render_map', ['render_map.pyx']),
		Extension('render_los', ['render_los.pyx']),
		Extension('render_fast_los', ['render_fast_los.pyx'])]
)
