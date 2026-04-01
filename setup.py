from setuptools import setup, find_packages

setup(
    name='open-claw',
    version='0.1.0',
    author='DecawDevonn',
    author_email='your_email@example.com',
    description='Open Claw - ai agent workforce system',
    long_description=open('README.md').read() if open('README.md', 'r') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/DecawDevonn/open-claw',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'Flask',
        'psycopg2-binary',
        'redis'
    ],
)