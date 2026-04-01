from setuptools import setup, find_packages

setup(
    name='open-claw',
    version='0.1.0',
    author='DecawDevonn',
    author_email='your_email@example.com',  # Replace with your email
    description='A brief description of the open-claw package.',
    long_description=open('README.md').read(),  # Assuming you have a README.md file
    long_description_content_type='text/markdown',
    url='https://github.com/DecawDevonn/open-claw',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'dependency1',  # Replace with actual dependencies
        'dependency2',
    ],
    entry_points={
        'console_scripts': [
            'open-claw=open_claw.main:main',  # Adjust according to your module structure
        ],
    },
)