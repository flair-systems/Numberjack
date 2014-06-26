#! /usr/bin/env python

'''
  Numberjack is a constraint satisfaction and optimisation library
  Copyright (C) 2009-2013 Cork Constraint Computation Center, UCC

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU Lesser General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Lesser General Public License for more details.
  You should have received a copy of the GNU Lesser General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

  The authors can be contacted electronically at
  numberjack.support@gmail.com
'''


from distutils.core import setup
from distutils.extension import Extension
from distutils.sysconfig import get_config_var
from distutils.command.build_ext import build_ext as _build_ext
import subprocess
import shutil
import sys
import os


USE_SYSTEM_LIBXML = False
THIRDPARTY = os.path.abspath('third-party')
LIBXMLSRCPATH = os.path.join(THIRDPARTY, "libxml2-2.9.1")
CPLEX, GUROBI = "CPLEX", "Gurobi"

EXTRA_COMPILE_ARGS = ['-O3']
EXTRA_LINK_ARGS = []
extensions = []

if sys.platform == 'darwin':
    EXTRA_COMPILE_ARGS.extend(
        ['-stdlib=libstdc++', '-Wno-shorten-64-to-32',
         '-arch', 'x86_64',  # force 64bit only builds on Mac

         # ignore warnings about swig code
         '-Wno-self-assign', '-Wno-shadow', '-Wno-unused-label',
         ])
    EXTRA_LINK_ARGS.extend(['-arch', 'x86_64', '-stdlib=libstdc++'])


# Custom class for build_ext command which will compile dependency libraries
# like libxml
class njbuild_ext(_build_ext):
    def run(self):
        if not USE_SYSTEM_LIBXML:
            build = self.get_finalized_command('build')
            xmldir = os.path.join(build.build_base, 'libxml')
            if not os.path.exists(xmldir):
                builddir = os.path.join(build.build_base, 'libxml-build')
                if os.path.exists(builddir):
                    shutil.rmtree(builddir)
                os.makedirs(builddir)

                cflags = get_config_var('CFLAGS')

                p = subprocess.Popen(
                    [os.path.join(LIBXMLSRCPATH, 'configure'),
                     '--enable-static',
                     '--prefix=%s' % os.path.abspath(xmldir),
                     'CFLAGS=%s' % cflags,
                     'CC=%s' % get_config_var('CC'),
                     ],
                    cwd=builddir)
                exitcode = p.wait()
                if exitcode != 0:
                    shutil.rmtree(builddir)
                    raise RuntimeError("libxml configure failed")
                p = subprocess.Popen(['make', 'install'], cwd=builddir)
                exitcode = p.wait()
                if exitcode != 0:
                    raise RuntimeError("libxml install failed")

            for ext in self.extensions:
                if ext.name == "_Mistral":
                    xml2configpath = os.path.join(xmldir, "bin", "xml2-config")
                    ext.extra_compile_args.extend(
                        xml2config('--cflags', path=xml2configpath))
                    ext.extra_link_args.extend(
                        xml2config('--libs', path=xml2configpath))

        _build_ext.run(self)


# ------------------------------ Helper Methods ------------------------------


def xml2config(option, path="xml2-config"):
    import shlex
    ln = os.popen('%s %s' % (path, option), 'r').readline()
    ln = ln.strip()
    return shlex.split(ln)


def get_solver_home(solvername):
    from distutils.spawn import find_executable

    if solvername == CPLEX:
        # Try for environmental variable first
        env_path = os.getenv('CPLEXDIR')
        if env_path and len(env_path.strip()) > 0:
            return env_path

        # Try to find the cplex binary in the PATH
        ex_path = find_executable('cplex')
        if ex_path:
            ex_path = os.path.realpath(ex_path)  # Expand symbolic links if any
            ex_dir = os.path.dirname(ex_path)  # Path to the bin directory
            return os.path.abspath(os.path.join(ex_dir, os.pardir, os.pardir))

    elif solvername == GUROBI:
        # Try for environmental variable first
        env_path = os.getenv('GUROBI_HOME')
        if env_path and len(env_path.strip()) > 0:
            return env_path

        # Try to find the gurobi_cl binary in the PATH
        ex_path = find_executable('gurobi_cl')
        if ex_path:
            ex_path = os.path.realpath(ex_path)  # Expand symbolic links if any
            ex_dir = os.path.dirname(ex_path)  # Path to the bin directory
            return os.path.abspath(os.path.join(ex_dir, os.pardir))
    else:
        raise RuntimeError("Error unknown solver name '%s'" % solvername)

    return None


# ------------------------------ Extensions ------------------------------


mistralsrc = 'Numberjack/solvers/Mistral/mistral/lib/src'
mistral = Extension(
    '_Mistral',
    sources=[
        'Numberjack/solvers/Mistral.i',
        'Numberjack/solvers/Mistral/Mistral.cpp',
    ] + [os.path.join(mistralsrc, bn) for bn in os.listdir(mistralsrc)],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/Mistral',
    ],
    include_dirs=[
        'Numberjack/solvers/Mistral',
        'Numberjack/solvers/Mistral/mistral/include',
    ],
    libraries=['m'],
    language='c++',
    define_macros=[('_UNIX', None)],
    extra_compile_args=EXTRA_COMPILE_ARGS +
    ['-fPIC', '-Wunused-label', '-fexceptions', '-Wno-overloaded-virtual'],
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(mistral)


mistral2src = 'Numberjack/solvers/Mistral2/mistral/src/lib'
mistral2 = Extension(
    '_Mistral2',
    sources=[
        'Numberjack/solvers/Mistral2.i',
        'Numberjack/solvers/Mistral2/Mistral2.cpp',
    ] + [os.path.join(mistral2src, bn) for bn in os.listdir(mistral2src)],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/Mistral2',
    ],
    include_dirs=[
        'Numberjack/solvers/Mistral2',
        'Numberjack/solvers/Mistral2/mistral/src/include',
        'Numberjack/solvers/Mistral2/mistral/tools/tclap/include'
    ],
    libraries=['m'],
    language='c++',
    # define_macros=[('_UNIX', None)],
    extra_compile_args=EXTRA_COMPILE_ARGS +
    ['-fPIC', '-Wunused-label', '-fexceptions', '-Wno-overloaded-virtual'],
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(mistral2)


toulbar2src = 'Numberjack/solvers/Toulbar2/lib/src'
toulbar2 = Extension(
    '_Toulbar2',
    sources=[
        'Numberjack/solvers/Toulbar2.i',
        'Numberjack/solvers/Toulbar2/Toulbar2.cpp',
    ] + [os.path.join(toulbar2src, bn) for bn in os.listdir(toulbar2src)],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/Toulbar2',
    ],
    include_dirs=[
        'Numberjack/solvers/Toulbar2',
        'Numberjack/solvers/Toulbar2/include',
    ],
    libraries=['gmp'],
    language='c++',
    define_macros=[
        ('NDEBUG', None),
        ('LINUX', None),
        ('LONGLONG_COST', None),
        ('WIDE_STRING', None),
        ('LONGDOUBLE_PROB', None),
        ('NARYCHAR', None)],
    extra_compile_args=EXTRA_COMPILE_ARGS + ['-Wno-overloaded-virtual'],
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(toulbar2)


mip = Extension(
    '_MipWrapper',
    sources=[
        'Numberjack/solvers/MipWrapper.i',
        'Numberjack/solvers/MipWrapper/MipWrapper.cpp',
    ],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/MipWrapper',
    ],
    include_dirs=['Numberjack/solvers/MipWrapper'],
    language='c++',
    extra_compile_args=EXTRA_COMPILE_ARGS,
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(mip)


sat = Extension(
    '_SatWrapper',
    sources=[
        'Numberjack/solvers/SatWrapper.i',
        'Numberjack/solvers/SatWrapper/SatWrapper.cpp',
    ],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/SatWrapper',
        '-INumberjack/solvers/MiniSat/minisat_src/core',
        '-INumberjack/solvers/MiniSat/minisat_src/mtl',
    ],
    include_dirs=[
        'Numberjack/solvers/SatWrapper/',
        'Numberjack/solvers/MiniSat/minisat_src/core',
        'Numberjack/solvers/MiniSat/minisat_src/mtl'
    ],
    language='c++',
    extra_compile_args=EXTRA_COMPILE_ARGS,
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(sat)


minisat = Extension(
    '_MiniSat',
    sources=[
        'Numberjack/solvers/MiniSat.i',
        'Numberjack/solvers/MiniSat/MiniSat.cpp',
        'Numberjack/solvers/SatWrapper/SatWrapper.cpp',
        'Numberjack/solvers/MiniSat/SimpSolver.cpp',
        'Numberjack/solvers/MiniSat/minisat_src/core/Solver.C',
    ],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/MiniSat',
        '-INumberjack/solvers/SatWrapper',
        '-INumberjack/solvers/MiniSat/minisat_src/core',
        '-INumberjack/solvers/MiniSat/minisat_src/mtl',
    ],
    include_dirs=[
        'Numberjack/solvers/MiniSat',
        'Numberjack/solvers/SatWrapper',
        'Numberjack/solvers/MiniSat/minisat_src/core',
        'Numberjack/solvers/MiniSat/minisat_src/mtl'
    ],
    language='c++',
    extra_compile_args=EXTRA_COMPILE_ARGS,
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(minisat)


walksat = Extension(
    '_Walksat',
    sources=[
        'Numberjack/solvers/Walksat.i',
        'Numberjack/solvers/Walksat/Walksat.cpp',
        'Numberjack/solvers/Walksat/walksat_src/cpp_walksat.cpp',
        'Numberjack/solvers/SatWrapper/SatWrapper.cpp',
    ],
    swig_opts=[
        '-modern', '-c++',
        '-INumberjack/solvers/Walksat',
        '-INumberjack/solvers/SatWrapper',
        '-INumberjack/solvers/Walksat/walksat_src',
        '-INumberjack/solvers/MiniSat/minisat_src/core',
        '-INumberjack/solvers/MiniSat/minisat_src/mtl',
    ],
    include_dirs=[
        'Numberjack/solvers/Walksat',
        'Numberjack/solvers/SatWrapper',
        'Numberjack/solvers/Walksat/walksat_src',
        'Numberjack/solvers/MiniSat/minisat_src/core',
        'Numberjack/solvers/MiniSat/minisat_src/mtl'
    ],
    language='c++',
    extra_compile_args=EXTRA_COMPILE_ARGS +
    ['-ffloat-store', '-Wno-format'],
    extra_link_args=EXTRA_LINK_ARGS,
)
extensions.append(walksat)

cplexhome = get_solver_home(CPLEX)
if cplexhome:
    concertdir = os.path.abspath(os.path.join(cplexhome, os.pardir, "concert"))

    def get_cplex_includes():
        cplexincdir = os.path.join(cplexhome, "include")
        concertincdir = os.path.join(concertdir, "include")
        return [cplexincdir, concertincdir]

    def get_cplex_lib_dirs():
        """
        CPLEX lib structure: cplexdir/lib/ARCHITECTURE/BUILDTYPE/
        This function will walk the cplexdir/lib folder to find the
        folders containing static libraries.
        """

        def getlibdirs(libfolder):
            for dirpath, dirnames, filenames in os.walk(libfolder):
                for f in filenames:
                    if f.endswith(".a"):
                        return str(dirpath)
            raise RuntimeError(
                "Error could not find the lib folder in %s" % cplexhome)

        cplexlibfolder = os.path.join(cplexhome, "lib")
        concertlibfolder = os.path.join(concertdir, "lib")
        return [getlibdirs(cplexlibfolder), getlibdirs(concertlibfolder)]

    cplex = Extension(
        '_CPLEX',
        sources=[
            'Numberjack/solvers/CPLEX.i',
            'Numberjack/solvers/CPLEX/CPLEX.cpp',
            'Numberjack/solvers/MipWrapper/MipWrapper.cpp',
        ],
        swig_opts=[
            '-modern', '-c++',
            '-INumberjack/solvers/CPLEX',
            '-INumberjack/solvers/MipWrapper',
        ],
        include_dirs=[
            'Numberjack/solvers/CPLEX',
            'Numberjack/solvers/MipWrapper',
        ] + get_cplex_includes(),
        library_dirs=get_cplex_lib_dirs(),
        language='c++',
        define_macros=[('_UNIX', None), ('NDEBUG', None), ('IL_STD', None)],
        extra_compile_args=EXTRA_COMPILE_ARGS +
        ['-O', '-fPIC', '-fexceptions', '-Qunused-arguments'] +
        ["-fno-strict-aliasing"] if sys.platform.startswith('linux') else [],
        libraries=['concert', 'ilocplex', 'cplex', 'm', 'pthread'],
        extra_link_args=EXTRA_LINK_ARGS,
    )
    extensions.append(cplex)
else:
    print "Could not locate CPLEX installation on your system, " \
        "the interface has been disabled."


gurobihome = get_solver_home(GUROBI)
if gurobihome:
    gurobiincdir = os.path.join(gurobihome, "include")
    gurobilibdir = os.path.join(gurobihome, "lib")

    def get_gurobi_libs():

        def get_gurobi_libname():
            import re
            libre = re.compile("lib(?P<libname>gurobi\d+)\.so")
            for dirpath, dirnames, filenames in os.walk(gurobilibdir):
                for f in filenames:
                    match = libre.match(f)
                    if match:
                        return match.groupdict()["libname"]
            raise RuntimeError(
                "Error could not find the Gurobi library in '%s'" %
                gurobilibdir)
        return ['gurobi_c++', get_gurobi_libname()]

    gurobi = Extension(
        '_Gurobi',
        sources=[
            'Numberjack/solvers/Gurobi.i',
            'Numberjack/solvers/Gurobi/Gurobi.cpp',
            'Numberjack/solvers/MipWrapper/MipWrapper.cpp',
        ],
        swig_opts=[
            '-modern', '-c++',
            '-INumberjack/solvers/Gurobi',
            '-INumberjack/solvers/MipWrapper',
        ],
        include_dirs=[
            'Numberjack/solvers/Gurobi',
            'Numberjack/solvers/MipWrapper',
            gurobiincdir,
        ],
        library_dirs=[gurobilibdir],
        libraries=get_gurobi_libs(),
        extra_compile_args=EXTRA_COMPILE_ARGS +
        ['-fPIC', '-fexceptions', '-Qunused-arguments'],
        extra_link_args=EXTRA_LINK_ARGS,
        language='c++',
    )
    extensions.append(gurobi)
else:
    print "Could not locate Gurboi installation on your system, " \
        "the interface has been disabled."


# ------------------------------ End Extensions ------------------------------


long_desc = """Numberjack is a modelling package written in Python for
constraint programming and combinatorial optimization. Python benefits from a
large and active programming community, Numberjack is therefore a perfect tool
to embed CP technology into larger applications. It is designed to support a
number of efficient underlying C/C++ solvers seamlessly and efficiently.
"""

lic = "License :: OSI Approved :: " \
    "GNU General Public License v2 or later (GPLv2+)"

setup(
    name='Numberjack',
    version='1.1.0',
    author='Numberjack Developers',
    packages=['Numberjack', 'Numberjack.solvers'],
    ext_modules=extensions,
    author_email='numberjack.support@gmail.com',
    url='http://numberjack.ucc.ie/',
    license=lic,
    description='A Python platform for combinatorial optimization.',
    long_description=long_desc,
    cmdclass={'build_ext': njbuild_ext},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: MacOS X",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: C",
        "Programming Language :: C++",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering",
        lic,
    ],
)
