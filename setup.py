from packaging.version import parse
from setuptools import find_packages, setup


with open('src/superannotate/version.py') as f:
    version = f.read().rstrip()[15:-1]

requirements_path = "requirements_{}.txt".format('dev' if parse(version).is_prerelease else 'prod')
requirements = []

with open("requirements.txt") as f:
    requirements.extend(f.read().splitlines())

with open(requirements_path) as f:
    requirements.extend(f.read().splitlines())


with open('README.md') as f:
    readme = f.read()

readme = "\n".join(readme.split('\n')[2:])


setup(
    name='superannotate',
    version=version,
    package_dir={"": "src"},
    package_data={"superannotate": ["logging.conf"]},
    packages=find_packages(where="src"),
    description='Python SDK to SuperAnnotate platform',
    license='MIT',
    author='SuperAnnotate AI',
    author_email='hovnatan@superannotate.com',
    url='https://github.com/superannotateai/superannotate-python-sdk',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    setup_requires=['wheel'],
    description_file="README.md",
    entry_points={
        'console_scripts': ['superannotatecli = superannotate.lib.app.bin.superannotate:main']
    },
    python_requires='>=3.6'
)
