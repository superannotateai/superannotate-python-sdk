from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read()

with open('README.md') as f:
    readme = f.read()

packages = find_packages()

setup(
    name='superannotate',
    version='0.1.3',
    description='Python SDK and CLI tools to SuperAnnotate platform',
    license='MIT',
    author='Hovnatan Karapetyan',
    author_email='hovnatan@superannotate.com',
    url='https://github.com/superannotateai/superannotate-python-sdk',
    download_url=
    'https://github.com/superannotateai/superannotate-python-sdk/archive/v0.1.3-beta.tar.gz',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    dependecy_links=[
        'git+https://github.com/cocodataset/panopticapi.git',
        'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'
    ],
    packages=find_packages(exclude=('tests', )),
    entry_points={
        'console_scripts': ['superannotate = superannotate.__main__:main']
    },
    python_requires='>=3.5'
)
