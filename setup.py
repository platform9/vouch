from setuptools import setup, find_packages

setup(
    name='vouch',
    version='0.1',
    description='',
    author='',
    author_email='',
    install_requires=[
        'cryptography==41.0.4',
        'keystonemiddleware==6.0.0',
        'Paste==3.0.8',
        'PasteDeploy==2.0.1',
        'prometheus-client==0.7.1',
        'pecan==1.3.2',
        'python-memcached==1.59'
    ],
    scripts=['bin/vouch', 'bin/init-region'],
    test_suite='nose.collector',
    tests_require=['nose', 'mock'],
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup'])
)
