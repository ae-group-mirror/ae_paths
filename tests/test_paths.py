""" ae.paths unit tests """
import glob
import os
import pathlib
import pytest
import shutil
from unittest.mock import patch

from ae.base import CFG_EXT, INI_EXT, TESTS_FOLDER, app_name_guess, os_platform, write_file
from ae.files import read_file_text, write_file_text, CachedFile, RegisteredFile
from ae.paths import (PATH_PLACEHOLDERS,
                      add_common_storage_paths, app_data_path, app_docs_path, coll_folders, coll_items,
                      copy_files, move_files,
                      normalize, path_files, path_folders, path_items, path_join, path_name, placeholder_key,
                      placeholder_path,
                      series_file_name, user_data_path, user_docs_path, Collector, FilesRegister)


file_root = 'TstRootFolder'
file_name = 'tst_file'
file_ext = '.xy'
file_without_properties = os.path.join(file_root, file_name + file_ext)
file_properties = {'int': 72, 'float': 1.5, 'str': 'value'}

root_files = ['setup.py']
mod_files = ['ae/paths.py']
tst_paths = ['tests']
tst_files = ['tests/conftest.py', 'tests/test_paths.py']
tst_sub_folder = 'tests/sub_dir'
tst_sub_py_files1 = [f'{tst_sub_folder}/tst_sub_file.py']
tst_sub_files1 = tst_sub_py_files1 + [f'{tst_sub_folder}/tst_sub_wo_extension']
tst_sub_sub_folder = f'{tst_sub_folder}/sub_dir2'
tst_sub_py_files2 = [f'{tst_sub_sub_folder}/tst_sub_sub_file.py']
tst_sub_files2 = tst_sub_py_files2 + [f'{tst_sub_sub_folder}/tst_sub_sub_wo_extension']
tst_sub_py_files = sorted([_ for _ in tst_sub_files1 + tst_sub_files2 if os.path.splitext(_)[1] == '.py'])
tst_all_py_files = sorted(root_files + mod_files + tst_files + tst_sub_py_files)

@pytest.fixture
def test_sub_files():
    """ provide deep folder test files with properties. """
    files = []
    os.mkdir(tst_sub_folder)
    for fn in tst_sub_files1:
        write_file(fn, f"file_content of sub {fn}")
        files.append(fn)
    os.mkdir(tst_sub_sub_folder)
    for fn in tst_sub_files2:
        write_file(fn, f"file_content of sub sub {fn}")
        files.append(fn)

    yield files

    shutil.rmtree(tst_sub_folder)


def property_matcher_mock(file):
    """ file property matcher mock. """
    return file.properties == file_properties


def file_loader_mock_func(file):
    """ cacheables file object loader mock function """
    return file


def file_sorter_mock(file):
    """ file sorter mock. """
    return file.properties.get('int', 0)


class TestHelpers:
    def test_path_join(self):
        assert path_join('') == os.path.join('')
        assert path_join('part') == os.path.join('part')
        assert path_join('part', 'part2') == os.path.join('part', 'part2')
        assert path_join('part', '', 'part2') == os.path.join('part', '', 'part2')
        assert path_join('part', '.', 'part2') == os.path.join('part', '.', 'part2')
        assert path_join('part', '..', 'part2') == os.path.join('part', '..', 'part2')
        assert path_join('part', '/part2') == os.path.join('part', '/part2')
        assert path_join('part', '/', 'part2') == os.path.join('part', '/', 'part2')
        assert path_join('part', '//', 'part2') == os.path.join('part', '//', 'part2')
        assert path_join('/part', 'part2') == os.path.join('/part', 'part2')
        assert path_join('', 'part2') == os.path.join('', 'part2')

        assert path_join('part', '') == 'part'  # os.path.join() returns 'part/' in this case
        assert path_join('part', '') != os.path.join('part', '')

    def test_path_name(self):
        assert path_name("") == ""
        assert path_name("/not/a/existing/test/path") == ""
        assert path_name(".") == ""

        duplicates1 = ('cwd', 'application')
        duplicates2 = ('doc', 'documents')
        for name, path in PATH_PLACEHOLDERS.items():
            if path_name(path) == 'external_storage':
                assert name == 'external_storage' or path.endswith(name)
            else:
                names = duplicates1 if name in duplicates1 else duplicates2 if name in duplicates2 else (name,)
                assert path_name(path) in names


class TestPlaceholders:
    def test_add_common_storage_paths(self):
        paths_count = len(PATH_PLACEHOLDERS)
        add_common_storage_paths()
        assert len(PATH_PLACEHOLDERS) > paths_count
        assert 'application' in PATH_PLACEHOLDERS
        if 'CI_PROJECT_ID' not in os.environ:           # skip on gitlab CI
            assert 'documents' in PATH_PLACEHOLDERS
            assert 'downloads' in PATH_PLACEHOLDERS
            assert 'external_storage' in PATH_PLACEHOLDERS
            assert 'home' in PATH_PLACEHOLDERS
            assert 'music' in PATH_PLACEHOLDERS
            assert 'pictures' in PATH_PLACEHOLDERS
            assert 'root' in PATH_PLACEHOLDERS
            assert 'videos' in PATH_PLACEHOLDERS
        if os_platform == 'android':
            assert 'sdcard' in PATH_PLACEHOLDERS

    def test_normalize(self):
        f_path = "norm_file.tst"
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False, remove_dots=False) == os.path.realpath(f_path)
        assert normalize(f_path, make_absolute=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False) == os.path.realpath(f_path)
        assert normalize(f_path, remove_dots=False, resolve_sym_links=False) == os.path.abspath(f_path)
        assert normalize(f_path, remove_dots=False) == os.path.realpath(f_path)
        assert normalize(f_path, resolve_sym_links=False) == os.path.abspath(f_path)
        assert normalize(f_path) == os.path.realpath(f_path)

        f_path = f"{TESTS_FOLDER}/norm_test.tst"
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False, remove_dots=False) == os.path.realpath(f_path)
        assert normalize(f_path, make_absolute=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False) == os.path.realpath(f_path)
        assert normalize(f_path, remove_dots=False, resolve_sym_links=False) == os.path.abspath(f_path)
        assert normalize(f_path, remove_dots=False) == os.path.realpath(f_path)
        assert normalize(f_path, resolve_sym_links=False) == os.path.abspath(f_path)
        assert normalize(f_path) == os.path.realpath(f_path)
        assert normalize(f_path, remove_base_path=TESTS_FOLDER) == "norm_test.tst"
        assert normalize(f_path, remove_base_path=TESTS_FOLDER) == os.path.relpath(f_path, TESTS_FOLDER)
        assert normalize(f_path, remove_base_path='_not_existing_') == f"../{TESTS_FOLDER}/" \
                                                                       f"{os.path.relpath(f_path, TESTS_FOLDER)}"
        assert f"../{TESTS_FOLDER}/{normalize(f_path, remove_base_path=TESTS_FOLDER)}" == os.path.relpath(
            f_path, "_not_exists_folder")

        f_path = f"_not_existing_folder/norm_test.tst"
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False, remove_dots=False) == os.path.realpath(f_path)
        assert normalize(f_path, make_absolute=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False) == os.path.realpath(f_path)
        assert normalize(f_path, remove_dots=False, resolve_sym_links=False) == os.path.abspath(f_path)
        assert normalize(f_path, remove_dots=False) == os.path.realpath(f_path)
        assert normalize(f_path, resolve_sym_links=False) == os.path.abspath(f_path)
        assert normalize(f_path) == os.path.realpath(f_path)
        assert normalize(f_path, remove_base_path=TESTS_FOLDER) == f"../{f_path}"
        assert normalize(f_path, remove_base_path=TESTS_FOLDER) == os.path.relpath(f_path, TESTS_FOLDER)
        assert normalize(f_path, remove_base_path='_not_existing_') == os.path.relpath(f_path, TESTS_FOLDER)
        assert normalize(f_path, remove_base_path=TESTS_FOLDER) == os.path.relpath(
            f_path, "_not_exists_folder")

        f_path = "~/normalize_test.tst"
        assert len(normalize(f_path)) > len(f_path)
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False).endswith(f_path[1:])
        assert normalize(f_path).endswith(f_path[1:])

        f_path = "."
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == "."
        assert len(normalize(f_path)) == len(os.getcwd())

        f_path = ""
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == "."
        assert len(normalize(f_path)) == len(os.getcwd())

    def test_placeholder_key(self):
        f_name = "test.tst"
        file_path = os.path.join(os.getcwd(), f_name)
        assert placeholder_key(f_name) == ""
        assert placeholder_key(file_path) == "cwd"
        assert placeholder_key(file_path).format(**PATH_PLACEHOLDERS) == "cwd"

    def test_placeholder_path(self):
        f_name = "test.tst"
        file_path = os.path.join(os.getcwd(), f_name)
        assert placeholder_path(f_name) == f_name
        assert placeholder_path(file_path) == "{cwd}" + os.path.sep + f_name
        assert placeholder_path(file_path).format(**PATH_PLACEHOLDERS) == file_path
        assert normalize(placeholder_path(file_path)) == file_path


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
        test_root = "/test_path"
        with patch('ae.paths.os_platform', 'cygwin'), patch.dict('os.environ', dict(APPDATA=test_root)):
            assert user_data_path() == test_root

    def test_user_data_path_darwin(self):
        with patch('ae.paths.os_platform', 'darwin'):
            assert user_data_path() == os.path.expanduser(os.path.join("~", "Library", "Application Support"))

    def test_user_data_path_ios(self):
        with patch('ae.paths.os_platform', 'ios'):
            assert user_data_path() == os.path.expanduser(os.path.join("~", "Documents"))

    def test_user_data_path_linux(self):  # or _freebsd or any other os
        test_path = ".config"
        with patch('ae.paths.os_platform', 'linux'), patch.dict('os.environ', dict(XDG_CONFIG_HOME=test_path)):
            assert user_data_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'linux'), patch.dict('os.environ', dict(XDG_CONFIG_HOME="")):
            assert user_data_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'freebsd'), patch.dict('os.environ', dict(XDG_CONFIG_HOME=test_path)):
            assert user_data_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'freebsd'), patch.dict('os.environ', dict(XDG_CONFIG_HOME="")):
            assert user_data_path().endswith(test_path)

    def test_user_data_path_win32(self):
        test_root = "/test_path"
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
        test_root = "/test_path"
        with patch('ae.paths.os_platform', 'cygwin'), patch.dict('os.environ', dict(USERPROFILE=test_root)):
            assert user_docs_path() == test_root + "/Documents"

    def test_user_docs_path_darwin(self):
        with patch('ae.paths.os_platform', 'darwin'):
            assert user_docs_path() == os.path.expanduser(os.path.join("~", "Documents"))

    def test_user_docs_path_ios(self):
        with patch('ae.paths.os_platform', 'ios'):
            assert user_docs_path() == os.path.expanduser(os.path.join("~", "Documents"))

    def test_user_docs_path_linux(self):  # or _freebsd or any other os
        test_path = "Documents"
        with patch('ae.paths.os_platform', 'linux'):
            assert user_docs_path().endswith(test_path)
        with patch('ae.paths.os_platform', 'freebsd'):
            assert user_docs_path().endswith(test_path)

    def test_user_docs_path_win32(self):
        test_root = "/test_path"
        with patch('ae.paths.os_platform', 'win32'), patch.dict('os.environ', dict(USERPROFILE=test_root)):
            assert user_docs_path() == test_root + "/Documents"


FILE0 = "app" + INI_EXT
CONTENT0 = "TEST FILE0 CONTENT"
OLD_CONTENT0 = "OLD/LOCKED FILE0 CONTENT"

DIR1 = "app_dir"
FILE1 = "app.png"
CONTENT1 = "TEST FILE1 CONTENT"

MOVES_SRC_FOLDER_NAME = "tst_move_path_source"
OVERWRITES_SRC_FOLDER_NAME = "tst_overwrite_path_source"


@pytest.fixture
def files_to_test():
    """ provide test file with properties. """
    fn = file_root
    os.mkdir(fn)
    write_file(file_without_properties, CONTENT0)

    for name, value in file_properties.items():
        fn = os.path.join(fn, name + '_' + str(value))
        os.mkdir(fn)
    fn = os.path.join(fn, file_name + file_ext)
    write_file(fn, CONTENT0)

    yield file_without_properties, fn

    shutil.rmtree(file_root)


@pytest.fixture(params=[MOVES_SRC_FOLDER_NAME, OVERWRITES_SRC_FOLDER_NAME])
def files_to_move(request, tmpdir):
    """ create test files in source directory to be moved and/or overwritten. """
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


class TestCopyFiles:
    def test_copy_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, "..")
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            assert not os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))
        tst_overwrite = (OVERWRITES_SRC_FOLDER_NAME in src_dir)

        copy_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            for src_file_path in files_to_move:
                assert os.path.exists(src_file_path)
                assert os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

    def test_blocked_copy_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, "..")
        dst_block_file = os.path.join(dst_dir, FILE0)
        write_file_text(OLD_CONTENT0, dst_block_file)
        assert os.path.exists(dst_block_file)
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            dst_file = os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os.path.exists(dst_file)
        tst_overwrite = (OVERWRITES_SRC_FOLDER_NAME in src_dir)

        copy_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            assert os.path.exists(files_to_move[0])
            assert read_file_text(files_to_move[0]) == CONTENT0
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[0], src_dir))
            assert os.path.exists(dst_file)
            assert read_file_text(dst_file) == OLD_CONTENT0

            assert os.path.exists(files_to_move[1])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[1], src_dir))
            assert os.path.exists(dst_file)
            assert read_file_text(dst_file) == CONTENT1


class TestMoveFiles:
    def test_moves_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, "..")
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            assert not os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))
        tst_overwrite = (OVERWRITES_SRC_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            for src_file_path in files_to_move:
                assert not os.path.exists(src_file_path)
                assert os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

    def test_blocked_moves_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, "..")
        dst_block_file = os.path.join(dst_dir, FILE0)
        write_file_text(OLD_CONTENT0, dst_block_file)
        assert os.path.exists(dst_block_file)
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            dst_file = os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os.path.exists(dst_file)
        tst_overwrite = (OVERWRITES_SRC_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            assert os.path.exists(files_to_move[0])
            assert read_file_text(files_to_move[0]) == CONTENT0
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[0], src_dir))
            assert os.path.exists(dst_file)
            assert read_file_text(dst_file) == OLD_CONTENT0

            assert not os.path.exists(files_to_move[1])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[1], src_dir))
            assert os.path.exists(dst_file)
            assert read_file_text(dst_file) == CONTENT1

    def test_overwrites_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, "..")
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            assert not os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))
        tst_overwrite = (OVERWRITES_SRC_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if tst_overwrite:
            for src_file_path in files_to_move:
                assert not os.path.exists(src_file_path)
                assert os.path.exists(os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir)))

    def test_unblocked_overwrites_to_parent_dir(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = os.path.join(src_dir, "..")
        dst_block_file = os.path.join(dst_dir, FILE0)
        write_file_text(OLD_CONTENT0, dst_block_file)
        assert os.path.exists(dst_block_file)
        for src_file_path in files_to_move:
            assert os.path.exists(src_file_path)
            dst_file = os.path.join(dst_dir, os.path.relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os.path.exists(dst_file)
        tst_overwrite = (OVERWRITES_SRC_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if tst_overwrite:
            assert not os.path.exists(files_to_move[0])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[0], src_dir))
            assert os.path.exists(dst_file)
            assert read_file_text(dst_file) == CONTENT0

            assert not os.path.exists(files_to_move[1])
            dst_file = os.path.join(dst_dir, os.path.relpath(files_to_move[1], src_dir))
            assert os.path.exists(dst_file)
            assert read_file_text(dst_file) == CONTENT1

    def test_file_moves_to_user_dir_via_check_all(self, files_to_move):
        src_dir = os.path.dirname(files_to_move[0])
        dst_dir = user_data_path()

        moved = []
        try:
            moved += move_files(src_dir, "{usr}")

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
        assert path_files("setup.py") == ["setup.py"]
        assert path_files("ae/paths.py") == ["ae/paths.py"]
        assert path_files("tests/test_paths.py") == ["tests/test_paths.py"]

        assert path_files("../ae_paths") == []
        assert path_files("../ae_paths/setup.py") == ["../ae_paths/setup.py"]

        assert path_files(".") == []
        assert all(_[0] == "." for _ in path_files("."))
        assert path_files("./setup.py") == ["./setup.py"]

        assert path_files("ae") == []
        assert "ae/paths.py" not in path_files("ae")        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_files("ae/paths.py") == ["ae/paths.py"]

        assert path_files("tests") == []
        assert "tests/test_paths.py" not in path_files("tests")
        assert path_files("tests/test_paths.py") == ["tests/test_paths.py"]

    def test_non_recursive(self):
        assert path_files("setup.py") == ["setup.py"]
        assert path_files("ae/paths.py") == ["ae/paths.py"]
        assert path_files("tests/test_paths.py") == ["tests/test_paths.py"]

        assert path_files("../ae_paths") == []
        assert path_files("../ae_paths/setup.py") == ["../ae_paths/setup.py"]

        assert path_files(".") == []
        assert path_files("./setup.py") == ["./setup.py"]
        assert path_files("./ae/paths.py") == ["./ae/paths.py"]

        assert path_files("ae") == []
        assert path_files("ae/paths.py") == ["ae/paths.py"]

        assert path_files("tests") == []
        assert path_files("tests/test_paths.py") == ["tests/test_paths.py"]

    def test_placeholders(self):
        assert len(path_files("{cwd}")) == len(path_files("."))
        assert path_files("{cwd}/ae/paths.py")[0].endswith("/ae_paths/ae/paths.py")

        assert len(path_files("{cwd}/**/*.py")) == 4    # ...setup.py, ...paths.py, ...test_paths.py, ...conftest.py
        assert all(_.endswith(".py") for _ in path_files("{cwd}/**/*.py"))
        assert all(_.startswith(os.path.sep) for _ in path_files("{cwd}/**/*.py"))

    def test_wildcards(self):
        assert path_files("*.py") == ["setup.py"]
        assert path_files("**.py") == ["setup.py"]

        assert path_files("set??.py") == ["setup.py"]
        assert path_files("setup*.py") == ["setup.py"]
        assert path_files("setup**.py") == ["setup.py"]

        assert "ae/paths.py" in path_files("ae/**")
        assert path_files("ae/**/*.py") == ["ae/paths.py"]
        assert path_files("**/pat?s.py") == ["ae/paths.py"]

        assert len(path_files("**/*.py")) == 4
        assert path_files("**/*.py") == ["setup.py", "ae/paths.py", "tests/test_paths.py", "tests/conftest.py"]

        assert path_files("{cwd}/**/paths.py")[0].endswith("ae_paths/ae/paths.py")
        assert path_files("{cwd}/**/paths.?y")[0].endswith("ae_paths/ae/paths.py")

        assert len(path_files("{cwd}/**/*paths.py")) == 2
        assert len(path_files("{cwd}/**/*paths.?y")) == 2

    def test_file_callable(self):
        def add_file(f_name, **kwargs):
            """ callable used for the file_class argument of path_files. """
            added.append((f_name, kwargs))
            return f_name
        added = []
        found = path_files("**.py", file_class=add_file, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == "setup.py"
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_files. """
            def __init__(self, f_name, **kwargs):
                self.file_name = f_name
                self.stem = os.path.splitext(f_name)[0]
                added.append((f_name, kwargs))
        added = []
        found = path_files("*.py", file_class=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].file_name == "setup.py"
        assert found[0].stem == "setup"
        assert added[0][0] == found[0].file_name
        assert added[0][1] == dict(a=3, b=6)

    def test_path_lib(self):
        found = path_files("*.py", file_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == "setup.py"
        assert found[0].stem == "setup"

        found = path_files("*.py", file_class=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == "setup.py"
        assert found[0].stem == "setup"


class TestPathFolders:
    def test_without_placeholders_and_wildcards(self):
        assert path_folders("setup.py") == []
        assert path_folders("ae/paths.py") == []
        assert path_folders("tests/test_paths.py") == []

        assert path_folders("../ae_paths") == ["../ae_paths"]
        assert path_folders("../ae_paths/setup.py") == []

        assert path_folders(".") == ["."]
        assert all(_[0] == "." for _ in path_folders("."))
        assert path_folders("./setup.py") == []

        assert path_folders("ae") == ["ae"]
        assert "ae/paths.py" not in path_folders("ae")        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_folders("ae/paths.py") == []

        assert path_folders("tests") == ["tests"]
        assert "tests/test_paths.py" not in path_folders("tests")
        assert path_folders("tests/test_paths.py") == []

    def test_non_recursive(self):
        assert path_folders("setup.py") == []
        assert path_folders("ae/paths.py") == []
        assert path_folders("tests/test_paths.py") == []

        assert path_folders("../ae_paths") == ["../ae_paths"]
        assert path_folders("../ae_paths/setup.py") == []

        assert path_folders(".") == ["."]
        assert path_folders("./setup.py") == []
        assert path_folders("./ae/paths.py") == []

        assert path_folders("ae") == ["ae"]
        assert path_folders("ae/paths.py") == []

        assert path_folders("tests") == ["tests"]
        assert path_folders("tests/test_paths.py") == []

    def test_placeholders(self):
        assert len(path_folders("{cwd}")) == len(path_folders("."))
        assert path_folders("{cwd}/ae")[0].endswith("/ae_paths/ae")

        assert path_folders("{cwd}/**")
        assert any(_.endswith("/ae_paths/ae") for _ in path_folders("{cwd}/**"))
        assert any(_.endswith("/ae_paths/tests") for _ in path_folders("{cwd}/**"))
        assert all(_.startswith(os.path.sep) for _ in path_folders("{cwd}/**"))

    def test_wildcards(self):
        assert path_folders("*.py") == []
        assert path_folders("**.py") == []

        assert path_folders("set??.py") == []
        assert path_folders("setup*.py") == []
        assert path_folders("setup**.py") == []

        assert "../ae_paths/ae" in path_folders("../ae_paths/**")
        assert "../ae_paths/ae/" in path_folders("../ae_paths/ae/**")

        assert path_folders("**")
        assert "ae" in path_folders("**")
        assert "tests" in path_folders("**")

        assert any(_.endswith("ae_paths/ae") for _ in path_folders("{cwd}/**"))
        assert any(_.endswith("ae_paths/ae/") for _ in path_folders("{cwd}/**/"))

    def test_folder_callable(self):
        def add_folder(folder_name, **kwargs):
            """ callable used for the file_class argument of path_folders. """
            added.append((folder_name, kwargs))
            return folder_name
        added = []
        found = path_folders("tests", folder_class=add_folder, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == "tests"
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_folders. """
            def __init__(self, f_name, **kwargs):
                self.folder_name = f_name
                self.stem = os.path.splitext(f_name)[0]
                added.append((f_name, kwargs))
        added = []
        found = path_folders("tests", folder_class=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].folder_name == "tests"
        assert found[0].stem == "tests"
        assert added[0][0] == found[0].folder_name
        assert added[0][1] == dict(a=3, b=6)

    def test_path_lib(self):
        found = path_folders("tests", folder_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == "tests"
        assert found[0].stem == "tests"

        found = path_folders("tests", folder_class=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == "tests"
        assert found[0].stem == "tests"


class TestPathItems:
    def test_without_placeholders_and_wildcards(self):
        assert path_items("setup.py") == ["setup.py"]
        assert path_items("ae/paths.py") == ["ae/paths.py"]
        assert path_items("tests/test_paths.py") == ["tests/test_paths.py"]

        assert path_items("../ae_paths") == ["../ae_paths"]
        assert path_items("../ae_paths/setup.py") == ["../ae_paths/setup.py"]

        assert path_items(".") == ["."]
        assert all(_[0] == "." for _ in path_items("."))
        assert path_items("./setup.py") == ["./setup.py"]

        assert path_items("ae") == ["ae"]
        assert "ae/paths.py" not in path_items("ae")        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_items("ae/paths.py") == ["ae/paths.py"]

        assert path_items("tests") == ["tests"]
        assert "tests/test_paths.py" not in path_items("tests")
        assert path_items("tests/test_paths.py") == ["tests/test_paths.py"]

    def test_non_recursive(self):
        assert path_items("setup.py") == ["setup.py"]
        assert path_items("ae/paths.py") == ["ae/paths.py"]
        assert path_items("tests/test_paths.py") == ["tests/test_paths.py"]

        assert path_items("../ae_paths") == ["../ae_paths"]
        assert path_items("../ae_paths/setup.py") == ["../ae_paths/setup.py"]

        assert path_items(".") == ["."]
        assert path_items("./setup.py") == ["./setup.py"]
        assert path_items("./ae/paths.py") == ["./ae/paths.py"]

        assert path_items("ae") == ["ae"]
        assert path_items("ae/paths.py") == ["ae/paths.py"]

        assert path_items("tests") == ["tests"]
        assert path_items("tests/test_paths.py") == ["tests/test_paths.py"]

    def test_placeholders(self):
        assert len(path_items("{cwd}")) == len(path_items("."))
        assert path_items("{cwd}/ae/paths.py")[0].endswith("/ae_paths/ae/paths.py")

        assert len(path_items("{cwd}/**/*.py")) == 4    # ...setup.py, ...paths.py, ...test_paths.py, ...conftest.py
        assert all(_.endswith(".py") for _ in path_items("{cwd}/**/*.py"))
        assert all(_.startswith(os.path.sep) for _ in path_items("{cwd}/**/*.py"))

    def test_wildcards(self):
        assert path_items("*.py") == ["setup.py"]
        assert path_items("**.py") == ["setup.py"]

        assert path_items("set??.py") == ["setup.py"]
        assert path_items("setup*.py") == ["setup.py"]
        assert path_items("setup**.py") == ["setup.py"]

        assert "ae/paths.py" in path_items("ae/**")
        assert path_items("ae/**/*.py") == ["ae/paths.py"]
        assert path_items("**/pat?s.py") == ["ae/paths.py"]

        assert len(path_items("**/*.py")) == 4
        assert path_items("**/*.py") == ["setup.py", "ae/paths.py", "tests/test_paths.py", "tests/conftest.py"]

        assert path_items("{cwd}/**/paths.py")[0].endswith("ae_paths/ae/paths.py")
        assert path_items("{cwd}/**/paths.?y")[0].endswith("ae_paths/ae/paths.py")

        assert len(path_items("{cwd}/**/*paths.py")) == 2
        assert len(path_items("{cwd}/**/*paths.?y")) == 2

    def test_file_callable(self):
        def add_file(f_name, **kwargs):
            """ callable used for the file_class argument of path_files. """
            added.append((f_name, kwargs))
            return f_name
        added = []
        found = path_items("**.py", creator=add_file, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == "setup.py"
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_files. """
            def __init__(self, f_name, **kwargs):
                self.file_name = f_name
                self.stem = os.path.splitext(f_name)[0]
                added.append((f_name, kwargs))
        added = []
        found = path_items("*.py", creator=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].file_name == "setup.py"
        assert found[0].stem == "setup"
        assert added[0][0] == found[0].file_name
        assert added[0][1] == dict(a=3, b=6)

    def test_path_lib(self):
        found = path_files("*.py", file_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == "setup.py"
        assert found[0].stem == "setup"

        found = path_items("*.py", creator=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == "setup.py"
        assert found[0].stem == "setup"


class TestSeriesFileName:
    def test_series_file_name_basics(self):
        assert series_file_name("tests/series_tests.tst") == "tests/series_tests 01.tst"
        assert series_file_name("tests/series_tests.tst", marker='_copy_') == "tests/series_tests_copy_01.tst"
        assert series_file_name("tests/series_tests.tst", digits=1) == "tests/series_tests 1.tst"

    def test_series_file_name_create(self):
        file_mask = "tests/series_tests*.tst"
        try:
            assert series_file_name("tests/series_tests.tst", create=True) == "tests/series_tests 01.tst"
            assert series_file_name("tests/series_tests.tst", create=True) == "tests/series_tests 02.tst"
        finally:
            for file in glob.glob(file_mask):
                os.remove(file)

    def test_series_file_name_conflict(self):
        file_mask = "tests/series_tests*.tst"
        try:
            open(file_mask.replace('*', ' aaa'), 'w').close()
            open(file_mask.replace('*', ' 04'), 'w').close()
            assert series_file_name("tests/series_tests.tst", create=True) == "tests/series_tests 03.tst"
            assert series_file_name("tests/series_tests.tst") == "tests/series_tests 05.tst"
        finally:
            for file in glob.glob(file_mask):
                os.remove(file)


class TestCollector:
    def test_add_placeholder(self):
        coll = Collector(app="tst_app_path", main_app_name="tst_app_name")
        assert "app" in coll.placeholders
        assert coll.placeholders["app"] == "tst_app_path"
        assert coll.placeholders["main_app_name"] == "tst_app_name"

    def test_collect_simplest(self):
        coll = Collector()  # item_collector=coll_files is the default argument -> no paths will be collected
        coll.collect('tests')
        assert coll.paths == []
        assert coll.files == []

        coll.collect('tests/*')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files + ['tests/requirements.txt'])

        coll.collect('tests/*.py')
        coll.collect('tests/*.txt')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(2 * (tst_files + ['tests/requirements.txt']))

    def test_collect_append_tests_files(self):
        coll = Collector()
        coll.collect('', append='tests')
        assert coll.paths == []

        coll.collect('tests', append='*.py')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files)

        coll.collect('', append='tests/*.py')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 2)

        coll.collect('tests')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == []

        coll.collect('tests', append='')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == []

        coll.collect('tests/*.py', append='')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 3)
        assert sorted(coll.selected) == []

        assert coll.failed == 1
        assert coll.error_message
        assert dict(coll.prefix_failed) == {'tests': 1}
        assert dict(coll.suffix_failed) == {'': 1}

    def test_collect_append_tests_folders(self):
        coll = Collector(item_collector=coll_folders)
        coll.collect('', append='tests')
        assert coll.paths == tst_paths

        coll.collect('tests', append='*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == []

        coll.collect('', append='tests/*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == []

        coll.collect('tests')
        assert coll.paths == tst_paths * 2
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == tst_paths

        coll.collect('tests', append='')
        assert coll.paths == tst_paths * 3
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == tst_paths

        coll.collect('tests/*.py', append='')
        assert coll.paths == tst_paths * 3
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == tst_paths

        assert coll.failed == 0
        assert not coll.error_message
        assert dict(coll.prefix_failed) == {}
        assert coll.suffix_failed == {}

    def test_collect_append_tests_items(self):
        coll = Collector(item_collector=coll_items)
        coll.collect('', append='tests')
        assert coll.paths == tst_paths

        coll.collect('tests', append='*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == sorted(tst_files)

        coll.collect('', append='tests/*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == sorted(tst_files * 2)

        coll.collect('tests')
        assert coll.paths == tst_paths * 2
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == tst_paths

        coll.collect('tests', append='')
        assert coll.paths == tst_paths * 3
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == tst_paths

        coll.collect('tests/*.py', append='')
        assert coll.paths == tst_paths * 3
        assert sorted(coll.files) == sorted(tst_files * 3)
        assert sorted(coll.selected) == tst_paths

        assert coll.failed == 0
        assert not coll.error_message
        assert dict(coll.prefix_failed) == {}
        assert coll.suffix_failed == {}

    def test_collect_select_tests_files(self):
        coll = Collector()      # item_collector=coll_files is the default argument
        coll.collect('', select='tests')
        assert coll.paths == []
        assert sorted(coll.selected) == []

        coll.collect('tests', select='*.py')
        assert coll.paths == []
        assert sorted(coll.files) == tst_files
        assert sorted(coll.selected) == tst_files

        coll.collect('', select='tests/*.py')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == sorted(tst_files * 2)

        coll.collect('tests', select='')
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == sorted(tst_files * 2)

        coll.collect('tests/*.py')      # collect select kwarg defaults to ''
        assert coll.paths == []
        assert sorted(coll.files) == sorted(tst_files * 3)
        assert sorted(coll.selected) == sorted(tst_files * 3)

        assert coll.failed == 2
        assert coll.error_message
        assert dict(coll.prefix_failed) == {'': 1, 'tests': 1}
        assert dict(coll.suffix_failed) == {'': 1, 'tests': 1}

    def test_collect_select_tests_folders(self):
        coll = Collector(item_collector=coll_folders)
        coll.collect('', select='tests')
        assert coll.paths == tst_paths
        assert sorted(coll.selected) == tst_paths

        coll.collect('tests', select='*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == ['tests']

        coll.collect('', select='tests/*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == sorted(tst_paths)

        coll.collect('tests', select='')
        assert coll.paths == tst_paths * 2
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == sorted(tst_paths * 2)

        coll.collect('tests/*.py')      # collect select kwarg defaults to ''
        assert coll.paths == tst_paths * 2
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == sorted(tst_paths * 2)

        assert coll.failed == 3
        assert coll.error_message
        assert dict(coll.prefix_failed) == {'': 1, 'tests/*.py': 1, 'tests': 1}
        assert dict(coll.suffix_failed) == {'': 1, 'tests/*.py': 1, '*.py': 1}

    def test_collect_select_tests_items(self):
        coll = Collector(item_collector=coll_items)
        coll.collect('', select='tests')
        assert coll.paths == tst_paths
        assert sorted(coll.selected) == tst_paths

        coll.collect('tests', select='*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == tst_files
        assert sorted(coll.selected) == tst_paths + tst_files

        coll.collect('', select='tests/*.py')
        assert coll.paths == tst_paths
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == sorted(tst_paths + tst_files * 2)

        coll.collect('tests', select='')
        assert coll.paths == tst_paths * 2
        assert sorted(coll.files) == sorted(tst_files * 2)
        assert sorted(coll.selected) == sorted(tst_paths * 2 + tst_files * 2)

        coll.collect('tests/*.py')      # collect select kwarg defaults to ''
        assert coll.paths == tst_paths * 2
        assert sorted(coll.files) == sorted(tst_files * 3)
        assert sorted(coll.selected) == sorted(tst_paths * 2 + tst_files * 3)

        assert coll.failed == 0
        assert not coll.error_message
        assert dict(coll.prefix_failed) == {}
        assert coll.suffix_failed == {}

    def test_collect_no_args(self):
        coll = Collector()
        coll.collect()
        assert not coll.paths
        assert not coll.files
        assert not coll.selected
        assert coll.failed == 0
        assert not coll.error_message
        assert len(coll.prefix_failed) == 0
        assert len(coll.suffix_failed) == 0

    def test_collect_nothing_found(self):
        coll = Collector(app="tst_app_path")
        prefixes = ("{cwd}/../..", "{app}", "{usr}", "{usr}/{app_name}", "{cwd}/..", "{cwd}", )
        coll.collect(*prefixes, append=(".app_env" + CFG_EXT, ".sys_env" + CFG_EXT, ".sys_envTEST" + CFG_EXT,))
        assert not coll.paths
        # global .app_env.cfg could be found on your local machine - therefore skip: assert not coll.files
        assert not coll.selected
        assert coll.failed == 0
        assert not coll.error_message
        assert not coll.prefix_failed
        assert len(coll.prefix_failed) == 0
        assert len(coll.suffix_failed) == 0

    def test_collect_appends(self):
        coll = Collector(item_collector=coll_items, app="ae", tst="tests")
        coll.collect("{app}", "ae", "", append=("{app_name}", "paths.py", "", "ae"), only_first_of=())
        assert coll.paths == ['ae', 'ae', '.', 'ae']
        assert coll.files == ['ae/paths.py', 'ae/paths.py']
        assert not coll.selected
        assert coll.failed == 0
        assert not coll.error_message

    def test_collect_appends_only_first(self):
        coll = Collector(app="ae", tst="tests")
        coll.collect("{app}", "ae", "", append=("{app_name}", "paths.py", "", "ae"))
        assert not coll.paths           # 'ae' not in coll.paths because prefix of ae/paths.py gets found before ""/ae
        assert coll.files == ['ae/paths.py']
        assert not coll.selected
        assert coll.failed == 0
        assert not coll.error_message

    def test_collect_append_string(self):
        coll = Collector(app="ae", tst="tests", main_app_name=__file__)
        coll.collect("{app}", "ae", "", append="{main_app_name}")
        assert not coll.paths
        assert len(coll.files) == 1       # ['{cwd}/tests/test_paths.py']
        assert coll.files[0].endswith('/ae_paths/tests/test_paths.py')
        assert not coll.selected
        assert coll.failed == 0
        assert not coll.error_message

    def test_collect_selects(self):
        coll = Collector(item_collector=coll_items, app="ae", tst="tests")
        coll.collect("{cwd}", "{app}", "ae",
                     select=(".*", "README.md", "tests/test_paths.py", "", "ae", ), only_first_of=())

        assert len(coll.paths) >= 4   # ['{cwd}', '{cwd}/ae', 'ae', 'ae'] + localMachFolders .git/.pylint/.mypy_cache/..
        assert sum(1 for _ in coll.paths if _ == os.getcwd()) == 1
        assert sum(1 for _ in coll.paths if _ == os.path.join(os.getcwd(), 'ae')) == 1
        assert sum(1 for _ in coll.paths if _ == 'ae') == 2

        assert 4 <= len(coll.files) <= 6    # .commit_msg.txt and .python-version are missing on CI host
        # ['{cwd}/.gitignore', '{cwd}/.commit_msg.txt', '{cwd}/.python-version', '{cwd}/.gitlab-ci.yml',
        #  '{cwd}/README.md', '{cwd}/tests/test_paths.py']
        assert all(_.startswith(os.getcwd()) for _ in coll.files)
        files = [os.path.basename(_) for _ in coll.files]
        assert '.gitignore' in files
        assert '.gitlab-ci.yml' in files
        assert 'README.md' in files
        assert 'test_paths.py' in files

        assert all(_ in coll.files or _ in coll.paths for _ in coll.selected)
        assert 0 < coll.failed < len(coll.paths) + len(coll.files)
        assert coll.error_message

    def test_collect_select_only_first(self):
        coll = Collector(app="ae", tst="tests")
        coll.collect("{cwd}", "{app}", "ae",
                     select=".*")
        assert not coll.paths
        assert 2 <= len(coll.files) <= 4
        # ['{cwd}/.gitignore', '{cwd}/.commit_msg.txt', '{cwd}/.python-version', '{cwd}/.gitlab-ci.yml']
        assert all(_.startswith(os.getcwd()) for _ in coll.files)
        files = [os.path.basename(_) for _ in coll.files]
        assert '.gitignore' in files
        assert '.gitlab-ci.yml' in files
        assert coll.selected == coll.files
        assert coll.failed == 0
        assert not coll.error_message

    def test_collect_select_string(self):
        coll = Collector(app="ae", tst="tests")
        coll.collect("{cwd}", "{app}", "ae",
                     select=".*", only_first_of=())
        assert not coll.paths
        assert 2 <= len(coll.files) <= 4
        # ['{cwd}/.gitignore', '{cwd}/.gitlab-ci.yml'] only .commit_msg.txt|.python-version not existing on CI host
        assert all(_.startswith(os.getcwd()) for _ in coll.files)
        files = [os.path.basename(_) for _ in coll.files]
        assert '.gitignore' in files
        assert '.gitlab-ci.yml' in files
        assert coll.selected == coll.files
        assert 0 < coll.failed <= len(coll.paths) + len(coll.files)  # failed == 2 from {app}.*|ae.* == ae.*|ae.*
        assert coll.error_message

    def test_collect_prefixes_only(self):
        coll = Collector(item_collector=coll_items, app="ae", tst="tests")
        coll.collect("{app}", "{usr}", 'tests/test_paths.py', only_first_of=())
        assert 1 <= len(coll.paths) <= 2   # ['ae', '/home/andi/.config']
        assert 'ae' in coll.paths
        assert coll.files == ['tests/test_paths.py']
        assert coll.selected == coll.paths + coll.files
        assert coll.failed == 0
        assert not coll.error_message

    def test_collect_prefixes_only_first_as_string(self):
        coll = Collector(item_collector=coll_folders, app="ae", tst="tests")
        coll.collect("{app}", "{usr}", "tests/test_paths.py", only_first_of="prefix")
        assert coll.paths == ['ae']
        assert not coll.files
        assert coll.selected == ['ae']
        assert coll.failed == 0
        assert not coll.error_message

    def test_wildcard_recursive(self, test_sub_files):
        coll = Collector()
        coll.collect('*.py')
        assert coll.files == ['setup.py']

        coll = Collector()
        coll.collect('', append='*.py')
        assert coll.files == ['setup.py']

        coll = Collector()
        coll.collect('**', append='*.py')
        assert sorted(coll.files) == tst_all_py_files

        coll = Collector()
        coll.collect('*', append='*.py')
        assert sorted(coll.files)  == sorted(mod_files + tst_files)

        coll = Collector()
        coll.collect('*/*', append='*.py')
        assert sorted(coll.files) == tst_sub_py_files1

        coll = Collector()
        coll.collect('*/*/*', append='*.py')
        assert sorted(coll.files) == tst_sub_py_files2

        coll = Collector()
        coll.collect('**/*', append='*.py')
        assert sorted(coll.files) == sorted(mod_files + tst_files + tst_sub_py_files)

        coll = Collector()
        coll.collect('*/**', append='*.py')
        assert sorted(coll.files) == sorted(mod_files + tst_files + tst_sub_py_files)

        assert coll.failed == 0
        assert not coll.error_message


class TestFilesRegister:
    """ test FilesRegister class. """
    def test_add_file(self):
        fr = FilesRegister()
        fr.add_file("test.xx")
        fr.add_file("test.yy")
        fr.add_file("test.yy")

        fr.add_file("test3")
        fr.add_file("test3.a")
        fr.add_file("test3.b")

        assert len(fr) == 2
        assert 'test' in fr
        assert 'test3' in fr
        assert fr.find_file('test')
        assert fr.find_file('test3')

        assert len(fr['test']) == 3
        assert fr['test'] == ['test.xx', 'test.yy', 'test.yy']

        assert len(fr['test3']) == 3
        assert fr['test3'] == ['test3', 'test3.a', 'test3.b']

        assert fr.find_file('test6') is None

    def test_add_file_reversed(self):
        fr = FilesRegister()
        fr.add_file("test.xx", first_index=-1)
        fr.add_file("test.yy", first_index=-2)
        fr.add_file("test.zz", first_index=-3)
        assert fr['test'] == ['test.zz', 'test.yy', 'test.xx']

    def test_add_files(self):
        fr = FilesRegister()
        files1 = ['tst.a', 'tst.b', 'tst.c']
        fr.add_files(files1)
        assert fr['tst'] == files1

        files2 = ['tst.1', 'tst.z', 'tst']
        fr.add_files(tuple(files2), first_index=0)
        assert fr['tst'] == files2 + files1

    def test_add_files_reversed(self):
        fr = FilesRegister()
        files1 = ['tst.a', 'tst.b', 'tst.c']
        fr.add_files(files1, first_index=-1)
        assert fr['tst'] == files1[::-1]

        files2 = ['tst.1', 'tst.z', 'tst']
        fr.add_files(tuple(files2), first_index=-4)
        assert fr['tst'] == (files1 + files2)[::-1]

    def test_add_register(self):
        fr = FilesRegister()
        fr.add_file("test.xx")
        fr.add_file("test.yy")
        fr.add_file("test3")

        fr2 = FilesRegister()
        fr2.add_file("dir/test.zz")
        fr2.add_file("dir3/test6")

        fr.add_register(fr2)
        assert len(fr) == 3
        assert len(fr['test']) == 3
        assert fr.find_file('test')
        assert fr.find_file('test3')
        assert fr.find_file('test6')

    def test_add_path_init(self, files_to_test):
        wop, wip = files_to_test
        fr = FilesRegister(os.path.join(file_root, '**'))
        assert len(fr) == 1
        assert file_name in fr
        files = fr[file_name]
        assert len(files) == 2
        assert all(_.path in (wop, wip) for _ in files)
        assert all(_.stem == file_name for _ in files)
        assert all(_.ext == file_ext for _ in files)
        assert all(_.properties in ({}, file_properties) for _ in files)

    def test_add_path_redirect(self, files_to_test):
        wop, wip = files_to_test
        fri = FilesRegister(os.path.join(file_root, '**'))
        fr = FilesRegister()
        assert len(fr.add_paths(os.path.join(file_root, '**'))) == len(files_to_test)
        assert len(fri) == len(fr)
        assert file_name in fr
        files = fr[file_name]
        assert len(files) == len(files_to_test)
        assert all(_.path in (wop, wip) for _ in files)
        assert all(_.stem == file_name for _ in files)
        assert all(_.ext == file_ext for _ in files)
        assert all(_.properties in ({}, file_properties) for _ in files)

        old_len = len(fr)
        assert 'test_files' not in fr
        fr.add_file('tests/test_files.py')
        assert old_len < len(fr)
        assert 'test_files' in fr

    def test_cache_file_class(self, files_to_test):
        wop, wip = files_to_test
        fr = FilesRegister(os.path.join(file_root, '**'), file_class=CachedFile, object_loader=file_loader_mock_func)
        assert len(fr) == 1
        assert file_name in fr
        files = fr[file_name]
        assert len(files) == 2
        assert all(_.path in (wop, wip) for _ in files)
        assert all(_.stem == file_name for _ in files)
        assert all(_.ext == file_ext for _ in files)
        assert all(_.properties in ({}, file_properties) for _ in files)

        assert all(isinstance(_, CachedFile) for _ in files)

    def test_call_find_file_redirect(self, files_to_test):
        assert file_name in files_to_test[1]
        fr = FilesRegister(file_root)
        assert fr(file_name, properties=file_properties) == fr.find_file(file_name, properties=file_properties)

    def test_find_file_by_name(self, files_to_test):
        assert file_name in files_to_test[1]
        fr = FilesRegister(os.path.join(file_root, '**'))
        assert fr.find_file(file_name).stem == file_name

    def test_find_file_by_properties(self, files_to_test):
        assert file_name in files_to_test[1]
        fr = FilesRegister(os.path.join(file_root, '**'))
        ff = fr.find_file(file_name, properties=file_properties)
        assert ff
        assert ff.stem == file_name
        assert ff.properties == file_properties

    def test_find_file_by_property_matcher(self, files_to_test):
        assert file_name in files_to_test[1]
        fr = FilesRegister(os.path.join(file_root, '**'))
        ff = fr.find_file(file_name, property_matcher=property_matcher_mock)
        assert ff
        assert ff.stem == file_name
        assert ff.properties == file_properties

    def test_find_file_by_property_matcher_and_file_sorter(self, files_to_test):
        assert file_name in files_to_test[1]
        fr = FilesRegister(os.path.join(file_root, '**'))
        ff = fr.find_file(file_name, properties=file_properties, file_sorter=file_sorter_mock)
        assert ff
        assert ff.stem == file_name
        assert ff.properties == file_properties

    def test_find_file_by_file_sorter(self, files_to_test):
        assert file_name in files_to_test[1]
        fr = FilesRegister(os.path.join(file_root, '**'))
        ff = fr.find_file(file_name, file_sorter=file_sorter_mock)
        assert ff
        assert ff.stem == file_name
        assert ff.properties == {}      # finds the one without properties because int-default==0

    def test_find_file_with_default_property_matcher(self):
        fr = FilesRegister(property_matcher=property_matcher_mock)
        assert fr.property_watcher is property_matcher_mock

    def test_find_file_with_default_file_sorter(self):
        fr = FilesRegister(file_sorter=file_sorter_mock)
        assert fr.file_sorter is file_sorter_mock

    def test_init_min(self):
        fr = FilesRegister()
        assert not fr.property_watcher
        assert not fr.file_sorter
        assert not fr.keys()
        assert not fr.values()

    def test_init_property_matcher(self):
        fr = FilesRegister(property_matcher=property_matcher_mock)
        assert fr.property_watcher is property_matcher_mock

    def test_init_file_sorter(self):
        fr = FilesRegister(file_sorter=file_sorter_mock)
        assert fr.file_sorter is file_sorter_mock

    def test_reclassify(self):
        fr = FilesRegister()
        fr.add_file('ttt')
        fr.add_file('dir/ttt')
        assert len(fr['ttt']) == 2

        assert all(isinstance(file, str) for file in fr['ttt'])
        fr.reclassify()
        assert all(isinstance(file, CachedFile) for file in fr['ttt'])
        fr.reclassify(file_class=RegisteredFile)
        assert all(isinstance(file, RegisteredFile) for file in fr['ttt'])
        fr.reclassify(file_class=pathlib.Path)
        assert all(isinstance(file, pathlib.Path) for file in fr['ttt'])
        fr.reclassify(file_class=pathlib.PurePath)
        assert all(isinstance(file, pathlib.PurePath) for file in fr['ttt'])
