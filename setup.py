from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read()

with open('README.md') as f:
    readme = f.read()

packages = find_packages()

setup(
    name='superannotate',
    version='1.0.0',
    description='Python SDK to annotate.online platform',
    license='GNU GPL 3',
    author='Hovnatan Karapetyan',
    author_email='hovnatan@superannotate.com',
    url='https://github.com/superannotateai/annotateonline-python-sdk',
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=('tests', )),
    entry_points={
        'console_scripts': ['superannotate = superannotate.__main__:main']
    },
    python_requires='>=3.5'
)
