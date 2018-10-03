from setuptools import setup

long_description = 'The official Python library for IPinfo. IPinfo prides itself on being the most reliable, accurate, and in-depth source of IP address data available anywhere. We process terabytes of data to produce our custom IP geolocation, company, carrier and IP type data sets. You can visit our developer docs at https://ipinfo.io/developers.'

setup(name='ipinfo',
      version='1.0.3',
      description='Official Python library for IPInfo',
      long_description=long_description,
      url='https://github.com/ipinfo/python',
      author='James Timmins',
      author_email='jameshtimmins@gmail.com',
      license='Apache License 2.0',
      packages=['ipinfo', 'ipinfo.cache'],
      install_requires=[
        'requests',
        'cachetools',
        'pytest',
      ],
      include_package_data=True,
      zip_safe=False)
