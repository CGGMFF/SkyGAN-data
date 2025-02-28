from setuptools import setup

setup(
    name='SkyGAN Data Pipeline',
    version='0.2.0',
    py_modules=['process_data'],
    install_requires=[
        'Click',
        'exifread',
        'tqdm',
        'numpy',
        'pandas',
    ],
    entry_points={
        'console_scripts': [
            'skygan_data = cli:cli',
        ],
    },
)
