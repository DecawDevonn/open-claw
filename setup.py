from setuptools import setup, find_packages

setup(
    name='open-claw',
    version='0.1.0',
    author='DecawDevonn',
    author_email='your_email@example.com',
    description='OpenClaw - Agent orchestration and task management platform',
    long_description=open('README.md').read(),
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
        'Flask>=3.0.0',
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'pydantic>=2.0.0',
        'click>=8.1.0',
        'colorama>=0.4.6',
        'tabulate>=0.9.0',
    ],
    extras_require={
        'dev': [
            'pytest>=8.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=7.0.0',
            'mypy>=1.0.0',
        ],
        'async': [
            'httpx>=0.27.0',
            'websockets>=12.0',
            'aiohttp>=3.13.3',
        ],
    },
    entry_points={
        'console_scripts': [
            'openclaw=cli:main',
        ],
    },
)
