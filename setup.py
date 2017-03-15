from setuptools import setup

setup(
    name='credpile',
    version='0.0.2',
    description='A utility for managing secrets in the cloud using AWS KMS and S3',
    license='Apache2',
    url='https://github.com/eversor1/credpile',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
    ],
    scripts=['credpile.py'],
    py_modules=['credpile'],
    install_requires=[
        'cryptography>=1.5, <2.0',
        'boto3>=1.1.1',
    ],
    extras_require={
        'YAML': ['PyYAML>=3.10']
    },
    entry_points={
        'console_scripts': [
            'credpile = credpile:main'
        ]
    }
)
