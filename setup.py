from setuptools import setup

setup(name='ipinfo_wrapper',
      version='0.1.3',
      description='Official Python library for IPinfo',
      url='https://github.com/ipinfo/python',
      author='James Timmins',
      author_email='jameshtimmins@gmail.com',
      license='Apache License 2.0',
      packages=['ipinfo_wrapper', 'ipinfo_wrapper.cache'],
      include_package_data=True,
      zip_safe=False)
