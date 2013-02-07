from setuptools import setup

version = '0.1'

setup(name='squash_python',
      version=version,
      description="Squash Client Library for Python",
      long_description=open("./README.md", "r").read(),
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Environment :: Console",
          "Intended Audience :: End Users/Desktop",
          "Natural Language :: English",
          "Operating System :: OS Independent",
          "Programming Language :: Python :: 2.7",
          "Topic :: Utilities",
          "License :: OSI Approved :: MIT License",
          ],
      keywords='exception error reporting squash',
      author='David Vierra',
      author_email='codewarrior0@gmail.com',
      url='https://github.com/codewarrior0/squash_python',
      license='MIT License',
      packages=["squash_python"],
      zip_safe=False,
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      squash_tester=squash_python.squash_tester:main
      squash_release=squash_python.squash_release:main

      """,
      )
