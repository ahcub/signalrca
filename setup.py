from os.path import join, dirname

from setuptools import setup, find_packages

with open(join(dirname(__file__), 'requirements.txt')) as requirements_file:
    install_reqs = [line.strip() for line in requirements_file]

print('install_reqs:', install_reqs)

with open('README.md') as file:
    long_description = file.read()


setup(
    name='signalrca',
    version='0.0.3',
    description='Async SignalR client for Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ahcub/signalrca',
    author='Alex Buchkovsky',
    author_email='alex.buchkovsky@gmail.com',
    license='Apache',
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords=['signalr', 'client', 'python', 'async'],
    packages=find_packages(),
    install_requires=install_reqs
)
