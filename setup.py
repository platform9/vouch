from setuptools import setup, find_packages

setup(
    name='vouch',
    version='0.1',
    description='',
    author='',
    author_email='',
    install_requires=[
        'cryptography==43.0.1', # https://pypi.org/project/cryptography/
        'keystonemiddleware==10.4.1', # https://pypi.org/project/keystonemiddleware/
        'Paste==3.7.1',
        'PasteDeploy==3.0.1',
        'prometheus-client==0.17.1', # https://pypi.org/project/prometheus-client/
        'pecan==1.5.1', # https://github.com/pecan/pecan/tags
        'python-memcached==1.59' #https://github.com/linsomniac/python-memcached/releases
    ],
    scripts=['bin/vouch', 'bin/common.py', 'bin/init-region', 'bin/renew-token'],
    test_suite='nose.collector',
    tests_require=['nose', 'mock'],
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup'])
)
