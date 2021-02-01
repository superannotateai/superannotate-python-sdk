import sys

from setuptools import find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read()
requirements = requirements.splitlines()

if sys.platform == 'linux':
    with open('requirements_extra.txt') as f:
        requirements_extra = f.read()

    requirements_extra = requirements_extra.splitlines()
    requirements += requirements_extra

with open('README.md') as f:
    readme = f.read()
readme = "\n".join(readme.split('\n')[2:])

packages = find_packages()

with open('superannotate/version.py') as f:
    Version = f.read()

Version = Version.rstrip()
Version = Version[15:-1]

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
    python_requires='>=3.6'
)
