from setuptools import setup, find_packages

setup(
    name='vouch',
    version='0.1',
    description='',
    author='',
    author_email='',
    install_requires=[
        'cryptography',
        'keystonemiddleware',
        'Paste',
        'PasteDeploy',
        'pecan',
        'python-memcached'
    ],
    scripts=['bin/vouch', 'bin/init-region'],
    test_suite='nose.collector',
    tests_require=['nose', 'mock'],
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup'])
)
