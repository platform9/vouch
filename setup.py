try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='vouch',
    version='0.1',
    description='',
    author='',
    author_email='',
    install_requires=[
        'python-memcached',
        'Paste',
        'PasteDeploy',
        'pecan',
        'keystonemiddleware'
    ],
    scripts=['bin/vouch'],
    test_suite='nose.collector',
    tests_require=['nose', 'mock'],
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup'])
)
