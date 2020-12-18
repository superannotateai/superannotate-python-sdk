import numpy as np
from setuptools import Extension, find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read()

requirements = requirements.splitlines()

with open('README.md') as f:
    readme = f.read()
readme = "\n".join(readme.split('\n')[2:])

packages = find_packages()

with open('superannotate/version.py') as f:
    Version = f.read()

Version = Version.rstrip()
Version = Version[15:-1]

ext_modules = [
    Extension(
        'superannotate.pycocotools_sa._mask',
        sources=[
            'superannotate/pycocotools_sa/_mask.pyx',
            'superannotate/pycocotools_sa/maskApi.c'
        ],
        include_dirs=[np.get_include(), 'superannotate/pycocotools_sa'],
        extra_compile_args=[],
    )
]

setup(
    name='superannotate',
    version=Version,
    description='Python SDK to SuperAnnotate platform',
    license='MIT',
    author='SuperAnnotate AI',
    author_email='hovnatan@superannotate.com',
    url='https://github.com/superannotateai/superannotate-python-sdk',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    setup_requires=['wheel'],
    packages=find_packages(exclude=('tests', )),
    entry_points={
        'console_scripts': ['superannotatecli = superannotate.__main__:main']
    },
    python_requires='>=3.6',
    ext_modules=ext_modules
)
