from setuptools import setup, find_packages

setup(
    name='open-claw',
    version='0.1.0',
    author='DecawDevonn',
    author_email='contact@openclaw.dev',
    description='AI agent workforce management system',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/DecawDevonn/open-claw',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    python_requires='>=3.10',
    install_requires=[
        'flask>=3.0',
        'gunicorn>=21.0',
    ],
    extras_require={
        'dev': ['pytest>=7.0', 'pytest-cov>=4.0', 'flake8>=6.0'],
        'mongo': ['pymongo>=4.0'],
    },
)
