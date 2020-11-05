""" ae.paths unit tests """
import pytest
import os
import pathlib
import shutil
from unittest.mock import patch

from ae.base import app_name_guess, os_platform
from ae.paths import (app_data_path, app_docs_path, move_path, path_files, path_folders, path_items,
                      user_data_path, user_docs_path, Collector)


class TestAppPaths:
    def test_app_data_path(self):
        assert app_data_path()
        assert app_data_path().endswith(app_name_guess())
        assert app_data_path().startswith(user_data_path())

    def test_app_docs_path(self):
        assert app_docs_path()
        assert app_docs_path().endswith(app_name_guess())
        assert app_docs_path().startswith(user_docs_path())


class TestUserDataPath:
    def test_user_data_path_android(self):
        if os_platform != 'android':
            pytest.skip("android-only test")
        with patch('ae.paths.os_platform', 'android'), patch.dict('os.environ', dict(ANDROID_ARGUMENT='any_value')):
            assert user_data_path()
        with patch('ae.paths.os_platform', 'android'), patch.dict('os.environ', dict(KIVY_BUILD='any_value')):
            assert user_data_path()

    def test_user_data_path_cygwin(self):
        test_root = '/test_path'
        with patch('ae.paths.os_platform', 'cygwin'), patch.dict('os.environ', dict(APPDATA=test_root)):
            assert user_data_path() == test_root

    def test_user_data_path_darwin(self):
        with patch('ae.paths.os_platform', 'darwin'):
            assert user_data_path() == os.path.expanduser(os.path.join('~', 'Library', 'Application Support'))

    def test_user_data_path_ios(self):
        with patch('ae.paths.os_platform', 'ios'):
            assert user_data_path() == os.path.expanduser(os.path.join('~', 'Documents'))

    def test_user_data_path_linux(self):  # or _freebsd or any other os
        test_path = '.config'
        with patch('ae.paths.os_platform', 'linux'), patch.dict('os.environ', dict(XDG_CONFIG_HOME=test_path)):
            assert user_data_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'linux'), patch.dict('os.environ', dict(XDG_CONFIG_HOME="")):
            assert user_data_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'freebsd'), patch.dict('os.environ', dict(XDG_CONFIG_HOME=test_path)):
            assert user_data_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'freebsd'), patch.dict('os.environ', dict(XDG_CONFIG_HOME="")):
            assert user_data_path().endswith(test_path)

    def test_user_data_path_win32(self):
        test_root = '/test_path'
        with patch('ae.paths.os_platform', 'win32'), patch.dict('os.environ', dict(APPDATA=test_root)):
            assert user_data_path() == test_root


class TestUserDocsPath:
    def test_user_docs_path_android(self):
        if os_platform != 'android':
            pytest.skip("android-only test")
        with patch('ae.paths.os_platform', 'android'), patch.dict('os.environ', dict(ANDROID_ARGUMENT='any_value')):
            assert user_docs_path()
        with patch('ae.paths.os_platform', 'android'), patch.dict('os.environ', dict(KIVY_BUILD='any_value')):
            assert user_docs_path()

    def test_user_docs_path_cygwin(self):
        test_root = '/test_path'
        with patch('ae.paths.os_platform', 'cygwin'), patch.dict('os.environ', dict(USERPROFILE=test_root)):
            assert user_docs_path() == test_root + '/Documents'

    def test_user_docs_path_darwin(self):
        with patch('ae.paths.os_platform', 'darwin'):
            assert user_docs_path() == os.path.expanduser(os.path.join('~', 'Documents'))

    def test_user_docs_path_ios(self):
        with patch('ae.paths.os_platform', 'ios'):
            assert user_docs_path() == os.path.expanduser(os.path.join('~', 'Documents'))

    def test_user_docs_path_linux(self):  # or _freebsd or any other os
        test_path = 'Documents'
        with patch('ae.paths.os_platform', 'linux'):
            assert user_docs_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'freebsd'):
            assert user_docs_path().endswith(test_path)

    def test_user_docs_path_win32(self):
        test_root = '/test_path'
        with patch('ae.paths.os_platform', 'win32'), patch.dict('os.environ', dict(USERPROFILE=test_root)):
            assert user_docs_path() == test_root + '/Documents'


FILE0 = 'app.ini'
CONTENT0 = "TEST FILE0 CONTENT"
OLD_CONTENT0 = "OLD/LOCKED FILE0 CONTENT"

DIR1 = 'app_dir'
FILE1 = 'app.png'
CONTENT1 = "TEST FILE1 CONTENT"

MOVES_SRC_FOLDER_NAME = 'tst_move_path_source'
OVERWRITES_SRC_FOLDER_NAME = 'tst_move_path_destination'


@pytest.fixture(params=[MOVES_SRC_FOLDER_NAME, OVERWRITES_SRC_FOLDER_NAME])
def files_to_move(request, tmpdir):
    """ create test files in source directory for to be moved and/or overwritten. """
    src_dir = tmpdir.mkdir(request.param)

    src_file1 = src_dir.join(FILE0)
    src_file1.write(CONTENT0)
    src_sub_dir = src_dir.mkdir(DIR1)
    src_file2 = src_sub_dir.join(FILE1)
    src_file2.write(CONTENT1)

    yield str(src_file1), str(src_file2)

    # tmpdir/dst_dir1 will be removed automatically by pytest - leaving the last three temporary directories
    # .. see https://docs.pytest.org/en/latest/tmpdir.html#the-default-base-temporary-directory
    # shutil.rmtree(tmpdir)


def _create_file_at_destination(dst_folder):
    """ create file0 at destination folder for to block move. """
    dst_file = os.path.join(dst_folder, FILE0)
    with open(dst_file, 'w') as fp:
        fp.write(OLD_CONTENT0)
    return dst_file


def _file_content(fn):
    with open(fn) as fp:
        fc = fp.read()
    return fc


class TestMovePath:
    def test_moves_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, '..')
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            assert not os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

        move_path(src_folder=src_dir, dst_folder=dst_dir)

        if MOVES_SRC_FOLDER_NAME in src_dir:
            for src_file_path in files_to_move:
                assert not os.path.exists(src_file_path)
                assert os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

    def test_blocked_moves_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, '..')
        dst_block_file = _create_file_at_destination(dst_dir)
        assert os.path.exists(dst_block_file)
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            dst_file = os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os.path.exists(dst_file)

        move_path(src_folder=src_dir, dst_folder=dst_dir)

        if MOVES_SRC_FOLDER_NAME in src_dir:
            assert os.path.exists(files_to_move[0])
            assert _file_content(files_to_move[0]) == CONTENT0
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[0], src_dir))
            assert os.path.exists(dst_file)
            assert _file_content(dst_file) == OLD_CONTENT0

            assert not os.path.exists(files_to_move[1])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[1], src_dir))
            assert os.path.exists(dst_file)
            assert _file_content(dst_file) == CONTENT1

    def test_overwrites_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, '..')
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            assert not os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

        move_path(src_folder=src_dir, dst_folder=dst_dir, overwrite=True)

        if OVERWRITES_SRC_FOLDER_NAME in src_dir:
            for src_file_path in files_to_move:
                assert not os.path.exists(src_file_path)
                assert os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

    def test_unblocked_overwrites_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, '..')
        dst_block_file = _create_file_at_destination(dst_dir)
        assert os.path.exists(dst_block_file)
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            dst_file = os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os.path.exists(dst_file)

        move_path(src_folder=src_dir, dst_folder=dst_dir, overwrite=True)

        if OVERWRITES_SRC_FOLDER_NAME in src_dir:
            assert not os.path.exists(files_to_move[0])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[0], src_dir))
            assert os.path.exists(dst_file)
            assert _file_content(dst_file) == CONTENT0

            assert not os.path.exists(files_to_move[1])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[1], src_dir))
            assert os.path.exists(dst_file)
            assert _file_content(dst_file) == CONTENT1

    def test_file_moves_to_user_dir_via_check_all(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = user_data_path()

        moved = list()
        try:
            moved += move_path(src_dir, "")

            for src_file_path in files_to_move:
                assert not os.path.exists(src_file_path)
                assert os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))
        finally:
            for dst_file_path in moved:
                dst_path = os.path.relpath(dst_file_path, dst_dir)
                if os.path.exists(dst_file_path):
                    os.remove(dst_file_path)
                    if dst_path != os.path.basename(dst_file_path):
                        shutil.rmtree(os.path.dirname(dst_file_path))


class TestPathFiles:
    def test_without_placeholders_and_wildcards(self):
        assert path_files('setup.py') == ['setup.py']
        assert path_files('ae/paths.py') == ['ae/paths.py']
        assert path_files('tests/test_paths.py') == ['tests/test_paths.py']

        assert path_files('../ae_paths') == []
        assert path_files('../ae_paths/setup.py') == ['../ae_paths/setup.py']

        assert path_files('.') == []
        assert all(_[0] == '.' for _ in path_files('.'))
        assert path_files('./setup.py') == ['./setup.py']

        assert path_files('ae') == []
        assert 'ae/paths.py' not in path_files('ae')        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_files('ae/paths.py') == ['ae/paths.py']

        assert path_files('tests') == []
        assert 'tests/test_paths.py' not in path_files('tests')
        assert path_files('tests/test_paths.py') == ['tests/test_paths.py']

    def test_non_recursive(self):
        assert path_files('setup.py', recursive=False) == ['setup.py']
        assert path_files('ae/paths.py', recursive=False) == ['ae/paths.py']
        assert path_files('tests/test_paths.py', recursive=False) == ['tests/test_paths.py']

        assert path_files('../ae_paths', recursive=False) == []
        assert path_files('../ae_paths/setup.py', recursive=False) == ['../ae_paths/setup.py']

        assert path_files('.', recursive=False) == []
        assert path_files('./setup.py', recursive=False) == ['./setup.py']
        assert path_files('./ae/paths.py', recursive=False) == ['./ae/paths.py']

        assert path_files('ae', recursive=False) == []
        assert path_files('ae/paths.py', recursive=False) == ['ae/paths.py']

        assert path_files('tests', recursive=False) == []
        assert path_files('tests/test_paths.py') == ['tests/test_paths.py']

    def test_placeholders(self):
        assert len(path_files('{cwd}')) == len(path_files('.'))
        assert path_files('{cwd}/ae/paths.py', recursive=False)[0].endswith('/ae_paths/ae/paths.py')

        assert len(path_files('{cwd}/**/*.py')) == 4    # ...setup.py, ...paths.py, ...test_paths.py, ...conftest.py
        assert all(_.endswith('.py') for _ in path_files('{cwd}/**/*.py'))
        assert all(_.startswith(os.path.sep) for _ in path_files('{cwd}/**/*.py'))

    def test_wildcards(self):
        assert path_files('*.py') == ['setup.py']
        assert path_files('**.py') == ['setup.py']

        assert path_files('set??.py') == ['setup.py']
        assert path_files('setup*.py') == ['setup.py']
        assert path_files('setup**.py') == ['setup.py']

        assert 'ae/paths.py' in path_files('ae/**')
        assert path_files('ae/**/*.py') == ['ae/paths.py']
        assert path_files('**/pat?s.py') == ['ae/paths.py']

        assert len(path_files('**/*.py')) == 4
        assert path_files('**/*.py') == ['setup.py', 'ae/paths.py', 'tests/test_paths.py', 'tests/conftest.py']

        assert path_files('{cwd}/**/paths.py')[0].endswith('ae_paths/ae/paths.py')
        assert path_files('{cwd}/**/paths.?y')[0].endswith('ae_paths/ae/paths.py')

        assert len(path_files('{cwd}/**/*paths.py')) == 2
        assert len(path_files('{cwd}/**/*paths.?y')) == 2

    def test_file_callable(self):
        def add_file(file_name, **kwargs):
            """ callable used for the file_class argument of path_files. """
            added.append((file_name, kwargs))
            return file_name
        added = list()
        found = path_files('**.py', file_class=add_file, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == 'setup.py'
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_files. """
            def __init__(self, file_name, **kwargs):
                self.file_name = file_name
                self.stem = os.path.splitext(file_name)[0]
                added.append((file_name, kwargs))
        added = list()
        found = path_files('*.py', file_class=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].file_name == 'setup.py'
        assert found[0].stem == 'setup'
        assert added[0][0] == found[0].file_name
        assert added[0][1] == dict(a=3, b=6)

    def test_path_lib(self):
        found = path_files('*.py', file_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == 'setup.py'
        assert found[0].stem == 'setup'

        found = path_files('*.py', file_class=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == 'setup.py'
        assert found[0].stem == 'setup'


class TestPathFolders:
    def test_without_placeholders_and_wildcards(self):
        assert path_folders('setup.py') == []
        assert path_folders('ae/paths.py') == []
        assert path_folders('tests/test_paths.py') == []

        assert path_folders('../ae_paths') == ['../ae_paths']
        assert path_folders('../ae_paths/setup.py') == []

        assert path_folders('.') == ['.']
        assert all(_[0] == '.' for _ in path_folders('.'))
        assert path_folders('./setup.py') == []

        assert path_folders('ae') == ['ae']
        assert 'ae/paths.py' not in path_folders('ae')        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_folders('ae/paths.py') == []

        assert path_folders('tests') == ['tests']
        assert 'tests/test_paths.py' not in path_folders('tests')
        assert path_folders('tests/test_paths.py') == []

    def test_non_recursive(self):
        assert path_folders('setup.py', recursive=False) == []
        assert path_folders('ae/paths.py', recursive=False) == []
        assert path_folders('tests/test_paths.py', recursive=False) == []

        assert path_folders('../ae_paths', recursive=False) == ['../ae_paths']
        assert path_folders('../ae_paths/setup.py', recursive=False) == []

        assert path_folders('.', recursive=False) == ['.']
        assert path_folders('./setup.py', recursive=False) == []
        assert path_folders('./ae/paths.py', recursive=False) == []

        assert path_folders('ae', recursive=False) == ['ae']
        assert path_folders('ae/paths.py', recursive=False) == []

        assert path_folders('tests', recursive=False) == ['tests']
        assert path_folders('tests/test_paths.py') == []

    def test_placeholders(self):
        assert len(path_folders('{cwd}')) == len(path_folders('.'))
        assert path_folders('{cwd}/ae', recursive=False)[0].endswith('/ae_paths/ae')

        assert path_folders('{cwd}/**')
        assert any(_.endswith('/ae_paths/ae') for _ in path_folders('{cwd}/**'))
        assert any(_.endswith('/ae_paths/tests') for _ in path_folders('{cwd}/**'))
        assert all(_.startswith(os.path.sep) for _ in path_folders('{cwd}/**'))

    def test_wildcards(self):
        assert path_folders('*.py') == []
        assert path_folders('**.py') == []

        assert path_folders('set??.py') == []
        assert path_folders('setup*.py') == []
        assert path_folders('setup**.py') == []

        assert '../ae_paths/ae' in path_folders('../ae_paths/**')
        assert '../ae_paths/ae/' in path_folders('../ae_paths/ae/**')

        assert path_folders('**')
        assert 'ae' in path_folders('**')
        assert 'tests' in path_folders('**')

        assert any(_.endswith('ae_paths/ae') for _ in path_folders('{cwd}/**'))
        assert any(_.endswith('ae_paths/ae/') for _ in path_folders('{cwd}/**/'))

    def test_folder_callable(self):
        def add_folder(folder_name, **kwargs):
            """ callable used for the file_class argument of path_folders. """
            added.append((folder_name, kwargs))
            return folder_name
        added = list()
        found = path_folders('tests', folder_class=add_folder, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == 'tests'
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_folders. """
            def __init__(self, file_name, **kwargs):
                self.folder_name = file_name
                self.stem = os.path.splitext(file_name)[0]
                added.append((file_name, kwargs))
        added = list()
        found = path_folders('tests', folder_class=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].folder_name == 'tests'
        assert found[0].stem == 'tests'
        assert added[0][0] == found[0].folder_name
        assert added[0][1] == dict(a=3, b=6)

    def test_path_lib(self):
        found = path_folders('tests', folder_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == 'tests'
        assert found[0].stem == 'tests'

        found = path_folders('tests', folder_class=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == 'tests'
        assert found[0].stem == 'tests'


class TestPathItems:
    def test_without_placeholders_and_wildcards(self):
        assert path_items('setup.py') == ['setup.py']
        assert path_items('ae/paths.py') == ['ae/paths.py']
        assert path_items('tests/test_paths.py') == ['tests/test_paths.py']

        assert path_items('../ae_paths') == ['../ae_paths']
        assert path_items('../ae_paths/setup.py') == ['../ae_paths/setup.py']

        assert path_items('.') == ['.']
        assert all(_[0] == '.' for _ in path_items('.'))
        assert path_items('./setup.py') == ['./setup.py']

        assert path_items('ae') == ['ae']
        assert 'ae/paths.py' not in path_items('ae')        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_items('ae/paths.py') == ['ae/paths.py']

        assert path_items('tests') == ['tests']
        assert 'tests/test_paths.py' not in path_items('tests')
        assert path_items('tests/test_paths.py') == ['tests/test_paths.py']

    def test_non_recursive(self):
        assert path_items('setup.py', recursive=False) == ['setup.py']
        assert path_items('ae/paths.py', recursive=False) == ['ae/paths.py']
        assert path_items('tests/test_paths.py', recursive=False) == ['tests/test_paths.py']

        assert path_items('../ae_paths', recursive=False) == ['../ae_paths']
        assert path_items('../ae_paths/setup.py', recursive=False) == ['../ae_paths/setup.py']

        assert path_items('.', recursive=False) == ['.']
        assert path_items('./setup.py', recursive=False) == ['./setup.py']
        assert path_items('./ae/paths.py', recursive=False) == ['./ae/paths.py']

        assert path_items('ae', recursive=False) == ['ae']
        assert path_items('ae/paths.py', recursive=False) == ['ae/paths.py']

        assert path_items('tests', recursive=False) == ['tests']
        assert path_items('tests/test_paths.py') == ['tests/test_paths.py']

    def test_placeholders(self):
        assert len(path_items('{cwd}')) == len(path_items('.'))
        assert path_items('{cwd}/ae/paths.py', recursive=False)[0].endswith('/ae_paths/ae/paths.py')

        assert len(path_items('{cwd}/**/*.py')) == 4    # ...setup.py, ...paths.py, ...test_paths.py, ...conftest.py
        assert all(_.endswith('.py') for _ in path_items('{cwd}/**/*.py'))
        assert all(_.startswith(os.path.sep) for _ in path_items('{cwd}/**/*.py'))

    def test_wildcards(self):
        assert path_items('*.py') == ['setup.py']
        assert path_items('**.py') == ['setup.py']

        assert path_items('set??.py') == ['setup.py']
        assert path_items('setup*.py') == ['setup.py']
        assert path_items('setup**.py') == ['setup.py']

        assert 'ae/paths.py' in path_items('ae/**')
        assert path_items('ae/**/*.py') == ['ae/paths.py']
        assert path_items('**/pat?s.py') == ['ae/paths.py']

        assert len(path_items('**/*.py')) == 4
        assert path_items('**/*.py') == ['setup.py', 'ae/paths.py', 'tests/test_paths.py', 'tests/conftest.py']

        assert path_items('{cwd}/**/paths.py')[0].endswith('ae_paths/ae/paths.py')
        assert path_items('{cwd}/**/paths.?y')[0].endswith('ae_paths/ae/paths.py')

        assert len(path_items('{cwd}/**/*paths.py')) == 2
        assert len(path_items('{cwd}/**/*paths.?y')) == 2

    def test_file_callable(self):
        def add_file(file_name, **kwargs):
            """ callable used for the file_class argument of path_files. """
            added.append((file_name, kwargs))
            return file_name
        added = list()
        found = path_items('**.py', creator=add_file, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == 'setup.py'
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_files. """
            def __init__(self, file_name, **kwargs):
                self.file_name = file_name
                self.stem = os.path.splitext(file_name)[0]
                added.append((file_name, kwargs))
        added = list()
        found = path_items('*.py', creator=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].file_name == 'setup.py'
        assert found[0].stem == 'setup'
        assert added[0][0] == found[0].file_name
        assert added[0][1] == dict(a=3, b=6)

    def test_path_lib(self):
        found = path_files('*.py', file_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == 'setup.py'
        assert found[0].stem == 'setup'

        found = path_items('*.py', creator=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == 'setup.py'
        assert found[0].stem == 'setup'


class TestCollector:
    def test_collect_placeholder(self):
        coll = Collector(app="tst_app_path", app_name="tst_app_name")
        assert 'app' in coll.placeholders
        assert coll.placeholders['app_name'] == "tst_app_name"

    def test_collect_nothing_found(self):
        coll = Collector(app="tst_app_path", app_name="tst_app_name")
        prefixes = ('{cwd}/../..', '{app}', '{usr}', '{usr}/{app_name}', '{cwd}/..', '{cwd}', )
        coll.collect(*prefixes, append=('.app_env.cfg', '.sys_env.cfg', '.sys_envTEST.cfg',))
        assert not coll.paths
        # global .app_env.cfg could be found on your local machine - therefore skip: assert not coll.files
        assert not coll.selected
        assert coll.failed == 0
        assert len(coll.prefix_failed) <= len(prefixes)
        assert any(count == 0 for count in coll.prefix_failed.values())
        assert len(coll.suffix_failed) == 0

    def test_collect_appends(self):
        coll = Collector(app="ae", tst='tests', app_name=__file__)
        coll.collect('{app}', "ae", '', append=('{app_name}', 'paths.py', "", "ae"), only_first_of=())
        assert coll.paths
        assert coll.files
        assert not coll.selected
        assert coll.failed == 0

    def test_collect_appends_only_first(self):
        coll = Collector(app="ae", tst='tests', app_name=__file__)
        coll.collect('{app}', "ae", '', append=('{app_name}', 'paths.py', "", "ae"))
        assert not coll.paths
        assert coll.files
        assert not coll.selected
        assert coll.failed == 0

    def test_collect_append_string(self):
        coll = Collector(app="ae", tst='tests', app_name=__file__)
        coll.collect('{app}', "ae", '', append='{app_name}')
        assert not coll.paths
        assert coll.files
        assert not coll.selected
        assert coll.failed == 0

    def test_collect_selects(self):
        coll = Collector(app="ae", tst='tests', app_name="tst_app_name")
        coll.collect('{cwd}', '{app}', "ae",
                     select=(".*", "README.md", "tests/test_paths.py", "", "ae", ), only_first_of=())
        assert coll.paths
        assert coll.files
        assert coll.selected
        assert 0 < coll.failed <= len(coll.paths) + len(coll.files)

    def test_collect_select_only_first(self):
        coll = Collector(app="ae", tst='tests', app_name="tst_app_name")
        coll.collect('{cwd}', '{app}', "ae",
                     select=".*")
        assert not coll.paths
        assert coll.files
        assert coll.selected
        assert coll.failed == 0

    def test_collect_select_string(self):
        coll = Collector(app="ae", tst='tests', app_name="tst_app_name")
        coll.collect('{cwd}', '{app}', "ae",
                     select=".*", only_first_of=())
        assert not coll.paths
        assert coll.files
        assert coll.selected
        assert 0 < coll.failed <= len(coll.paths) + len(coll.files)

    def test_collect_prefixes_only(self):
        coll = Collector(app="ae", tst='tests', app_name="tst_app_name")
        coll.collect('{app}', '{usr}', "tests/test_paths.py", only_first_of=())
        assert coll.paths
        assert not coll.files
        assert coll.selected
        assert 0 < coll.failed < len(coll.paths) + len(coll.files)

    def test_collect_prefixes_only_first_as_string(self):
        coll = Collector(app="ae", tst='tests', app_name="tst_app_name")
        coll.collect('{app}', '{usr}', "tests/test_paths.py", only_first_of="prefix")
        assert coll.paths
        assert not coll.files
        assert coll.selected
        assert coll.failed == 0
