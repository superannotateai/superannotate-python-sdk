import os
import re

from setuptools import find_packages, setup


def get_version():
    init = open(os.path.join(os.path.dirname(__file__), 'src', 'superannotate', '__init__.py')).read()
    version_re = re.compile(r'''__version__ = ["']((\d+)\.(\d+)\.(\d+)((dev(\d+))?(b(\d+))?))['"]''')
    return version_re.search(init).group(1)


sdk_version = get_version()

requirements = []

with open("requirements.txt") as f:
    requirements.extend(f.read().splitlines())

with open('README.md') as f:
    readme = f.read()

readme = "\n".join(readme.split('\n')[2:])

setup(
    name='superannotate',
    version=sdk_version,
    package_dir={"": "src"},
    package_data={"superannotate": ["logging.conf"]},
    packages=find_packages(where="src"),
    description='Python SDK to SuperAnnotate platform',
    license='MIT',
    author='SuperAnnotate AI',
    url='https://github.com/superannotateai/superannotate-python-sdk',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    setup_requires=['wheel'],
    description_file="README.md",
    entry_points={
        'console_scripts': ['superannotatecli = superannotate.lib.app.bin.superannotate:main']
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    project_urls={
        'Documentation': 'https://superannotate.readthedocs.io/en/stable/',
    },
    python_requires='>=3.7'
)
