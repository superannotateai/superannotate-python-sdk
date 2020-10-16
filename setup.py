from setuptools import setup, find_packages

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

setup(
    name='superannotate',
    version=Version,
    description='Python SDK to SuperAnnotate platform',
    license='MIT',
    author='Hovnatan Karapetyan',
    author_email='hovnatan@superannotate.com',
    url='https://github.com/superannotateai/superannotate-python-sdk',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    setup_requires=['wheel'],
    packages=find_packages(exclude=('tests', )),
    entry_points={
        'console_scripts': ['superannotate = superannotate.__main__:main']
    },
    python_requires='>=3.6'
)
