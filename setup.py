# THIS FILE IS EXCLUSIVELY MAINTAINED by the project aedev.tpl_project V0.3.35
""" setup of ae namespace module portion paths: generic file path helpers. """



# noinspection PyUnresolvedReferences
import setuptools

setup_kwargs = {
    'author': 'AndiEcker',
    'author_email': 'aecker2@gmail.com',
    'classifiers': ['Development Status :: 3 - Alpha', 'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)', 'Natural Language :: English', 'Operating System :: OS Independent', 'Programming Language :: Python', 'Programming Language :: Python :: 3', 'Programming Language :: Python :: 3.9', 'Topic :: Software Development :: Libraries :: Python Modules'],
    'description': 'ae namespace module portion paths: generic file path helpers',
    'extras_require': {'dev': ['aedev_tpl_project', 'ae_ae', 'anybadge', 'coverage-badge', 'aedev_git_repo_manager', 'flake8', 'mypy', 'pylint', 'pytest', 'pytest-cov', 'pytest-django', 'typing', 'types-setuptools', 'wheel', 'twine'], 'docs': [], 'tests': ['anybadge', 'coverage-badge', 'aedev_git_repo_manager', 'flake8', 'mypy', 'pylint', 'pytest', 'pytest-cov', 'pytest-django', 'typing', 'types-setuptools', 'wheel', 'twine']},
    'install_requires': ['ae_base', 'ae_files'],
    'keywords': ['configuration', 'development', 'environment', 'productivity'],
    'license': 'OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'long_description': '<!-- THIS FILE IS EXCLUSIVELY MAINTAINED by the project ae.ae V0.3.96 -->\n<!-- THIS FILE IS EXCLUSIVELY MAINTAINED by the project aedev.tpl_namespace_root V0.3.14 -->\n# paths 0.3.42\n\n[![GitLab develop](https://img.shields.io/gitlab/pipeline/ae-group/ae_paths/develop?logo=python)](\n    https://gitlab.com/ae-group/ae_paths)\n[![LatestPyPIrelease](\n    https://img.shields.io/gitlab/pipeline/ae-group/ae_paths/release0.3.41?logo=python)](\n    https://gitlab.com/ae-group/ae_paths/-/tree/release0.3.41)\n[![PyPIVersions](https://img.shields.io/pypi/v/ae_paths)](\n    https://pypi.org/project/ae-paths/#history)\n\n>ae namespace module portion paths: generic file path helpers.\n\n[![Coverage](https://ae-group.gitlab.io/ae_paths/coverage.svg)](\n    https://ae-group.gitlab.io/ae_paths/coverage/index.html)\n[![MyPyPrecision](https://ae-group.gitlab.io/ae_paths/mypy.svg)](\n    https://ae-group.gitlab.io/ae_paths/lineprecision.txt)\n[![PyLintScore](https://ae-group.gitlab.io/ae_paths/pylint.svg)](\n    https://ae-group.gitlab.io/ae_paths/pylint.log)\n\n[![PyPIImplementation](https://img.shields.io/pypi/implementation/ae_paths)](\n    https://gitlab.com/ae-group/ae_paths/)\n[![PyPIPyVersions](https://img.shields.io/pypi/pyversions/ae_paths)](\n    https://gitlab.com/ae-group/ae_paths/)\n[![PyPIWheel](https://img.shields.io/pypi/wheel/ae_paths)](\n    https://gitlab.com/ae-group/ae_paths/)\n[![PyPIFormat](https://img.shields.io/pypi/format/ae_paths)](\n    https://pypi.org/project/ae-paths/)\n[![PyPILicense](https://img.shields.io/pypi/l/ae_paths)](\n    https://gitlab.com/ae-group/ae_paths/-/blob/develop/LICENSE.md)\n[![PyPIStatus](https://img.shields.io/pypi/status/ae_paths)](\n    https://libraries.io/pypi/ae-paths)\n[![PyPIDownloads](https://img.shields.io/pypi/dm/ae_paths)](\n    https://pypi.org/project/ae-paths/#files)\n\n\n## installation\n\n\nexecute the following command to install the\nae.paths module\nin the currently active virtual environment:\n \n```shell script\npip install ae-paths\n```\n\nif you want to contribute to this portion then first fork\n[the ae_paths repository at GitLab](\nhttps://gitlab.com/ae-group/ae_paths "ae.paths code repository").\nafter that pull it to your machine and finally execute the\nfollowing command in the root folder of this repository\n(ae_paths):\n\n```shell script\npip install -e .[dev]\n```\n\nthe last command will install this module portion, along with the tools you need\nto develop and run tests or to extend the portion documentation. to contribute only to the unit tests or to the\ndocumentation of this portion, replace the setup extras key `dev` in the above command with `tests` or `docs`\nrespectively.\n\nmore detailed explanations on how to contribute to this project\n[are available here](\nhttps://gitlab.com/ae-group/ae_paths/-/blob/develop/CONTRIBUTING.rst)\n\n\n## namespace portion documentation\n\ninformation on the features and usage of this portion are available at\n[ReadTheDocs](\nhttps://ae.readthedocs.io/en/latest/_autosummary/ae.paths.html\n"ae_paths documentation").\n',
    'long_description_content_type': 'text/markdown',
    'name': 'ae_paths',
    'package_data': {'': []},
    'packages': ['ae'],
    'project_urls': {'Bug Tracker': 'https://gitlab.com/ae-group/ae_paths/-/issues', 'Documentation': 'https://ae.readthedocs.io/en/latest/_autosummary/ae.paths.html', 'Repository': 'https://gitlab.com/ae-group/ae_paths', 'Source': 'https://ae.readthedocs.io/en/latest/_modules/ae/paths.html'},
    'python_requires': '>=3.9',
    'setup_requires': ['aedev_setup_project'],
    'url': 'https://gitlab.com/ae-group/ae_paths',
    'version': '0.3.42',
    'zip_safe': True,
}

if __name__ == "__main__":
    setuptools.setup(**setup_kwargs)
    pass
