""" ae.paths unit tests """
import os
import pathlib
import shutil

import pytest
import sys
import types
from ctypes import create_unicode_buffer
from typing import Any
from unittest.mock import patch, MagicMock

from ae.base import (
    UNSET,
    format_given, os_path_abspath, os_path_basename, os_path_dirname, os_path_expanduser, os_path_isfile, os_path_isdir,
    os_path_join, os_path_realpath, os_path_relpath, os_path_splitext, write_file)
from ae.system import app_name_guess, os_platform 
from ae.files import read_file_text, write_file_text, CachedFile, RegisteredFile

from ae.paths import (
    I18N_FOLDER, IMAGE_FOLDER, PATH_PLACEHOLDERS, RESOURCES_NAMES, SOUND_FOLDER,
    add_common_storage_paths, app_data_path, app_docs_path, coll_files, coll_folders, coll_items, coll_item_type,
    copy_files, move_files, normalize, path_files, path_folders, path_items, path_join, path_match,
    path_name, paths_match, placeholder_key, placeholder_path, series_file_name, relative_file_paths,
    resources_folder_names, skip_py_cache_files, user_data_path, user_docs_path,
    Collector, FilesRegister)

try:
    import plyer
    plyer_is_importable = True
except (ModuleNotFoundError, ImportError):
    plyer_is_importable = False


# used project root folders/files for unit tests
TST_MODULE = "ae/paths" + '.py'
TST_SETUP = "setup" + '.py'
TST_FOLDER_TESTS = 'tests'
TST_TESTS_MODULE = os_path_join(TST_FOLDER_TESTS, "test_paths" + '.py')
TST_TESTS_CONF_PATH = os_path_join(TST_FOLDER_TESTS, "conftest" + '.py')
TST_TESTS_REQS_PATH = os_path_join(TST_FOLDER_TESTS, "requirements.txt")
TST_TESTS_PY_FILES = [TST_TESTS_CONF_PATH, TST_TESTS_MODULE]


TST_TMP_ROOT = "tst_session_tmp_path"       # temp path/dir with session scope, initialized via _session_tmp_dir()


@pytest.fixture(scope="session", autouse=True)
def _session_tmp_dir(tmp_path_factory):
    global TST_TMP_ROOT
    TST_TMP_ROOT = str(tmp_path_factory.mktemp(TST_TMP_ROOT))


TST_PROP_ROOT = 'TstRootFolder'
TST_PROP_FILE = 'tst_file'
TST_PROP_EXT = '.xy'
TST_FILE_WITHOUT_PROPS = os_path_join(TST_PROP_ROOT, TST_PROP_FILE + TST_PROP_EXT)
TST_PROPERTIES = {'int': 72, 'float': 1.5, 'str': 'value'}


@pytest.fixture
def tst_prop_files(monkeypatch, tmp_path):
    """ provide a test file with properties in temporary cwd """
    monkeypatch.chdir(tmp_path)
    fn = TST_PROP_ROOT
    os.mkdir(fn)
    write_file(TST_FILE_WITHOUT_PROPS, TST_FILE_CONTENT)

    for name, value in TST_PROPERTIES.items():
        fn = os_path_join(fn, name + "_" + str(value))
        os.mkdir(fn)

    fn = os_path_join(fn, TST_PROP_FILE + TST_PROP_EXT)
    write_file(fn, TST_FILE_CONTENT)

    yield TST_FILE_WITHOUT_PROPS, fn


TST_OVER_FOLDER_NAME = "tst_ae_paths_over_src"
TST_INI_FILE = "tst_app" + '.ini'
TST_FILE_CONTENT = "TEST FILE CONTENT"
TST_OLD_CONTENT = "OLD/LOCKED TEST FILE CONTENT"
TST_NEW_CONTENT = "NEW TEST FILE CONTENT"


@pytest.fixture(params=["tst_ae_paths_src", TST_OVER_FOLDER_NAME])
def tst_move_files(request, tmp_path):
    """ create test files in a temporary source directory to be moved and/or overwritten. """
    src_dir = tmp_path / request.param
    src_dir.mkdir()

    src_file1 = src_dir / TST_INI_FILE
    src_file1.write_text(TST_FILE_CONTENT)
    src_sub_dir = src_dir / "tst_app_dir"
    src_sub_dir.mkdir()
    src_file2 = src_sub_dir / "tst_app.png"
    src_file2.write_text(TST_NEW_CONTENT)

    yield str(src_file1), str(src_file2)


def tst_property_matcher(file):
    """ file property tests matcher """
    return file.properties == TST_PROPERTIES


def tst_file_loader(file):
    """ cacheables file object loader tests function """
    return file


def tst_file_sorter(file):
    """ tests file sorter """
    return file.properties.get('int', 0)


class TestAddCommonStoragePaths:
    @pytest.fixture(autouse=True)
    def reset_paths(self):
        """ restore module-load/initial PATH_PLACEHOLDERS """
        paths = PATH_PLACEHOLDERS.copy()
        yield
        PATH_PLACEHOLDERS.clear()
        PATH_PLACEHOLDERS.update(paths)

    def test_add_common_storage_paths_plyer(self):
        storagepath = types.SimpleNamespace(
            get_application_dir=lambda: '/application',
            get_documents_dir=lambda: '/documents',
            get_downloads_dir=lambda: '/downloads',
            get_external_storage_dir=lambda: '/external',
            get_home_dir=lambda: '/home',
            get_music_dir=lambda: '/music',
            get_pictures_dir=lambda: '/pictures',
            get_root_dir=lambda: '/root',
            get_videos_dir=lambda: '/videos',
            get_sdcard_dir=lambda: None,
            get_invalid_dir=lambda: 123,
        )
        mock_plyer = types.ModuleType('plyer')
        mock_plyer.storagepath = storagepath

        with (patch.dict(sys.modules, {'plyer': mock_plyer}),
              patch('ae.paths.os_platform', 'other')):
            add_common_storage_paths()

        assert PATH_PLACEHOLDERS['application'] == '/application'
        assert PATH_PLACEHOLDERS['documents'] == '/documents'
        assert PATH_PLACEHOLDERS['downloads'] == '/downloads'
        assert PATH_PLACEHOLDERS['external_storage'] == '/external'
        assert PATH_PLACEHOLDERS['home'] == '/home'
        assert PATH_PLACEHOLDERS['music'] == '/music'
        assert PATH_PLACEHOLDERS['pictures'] == '/pictures'
        assert PATH_PLACEHOLDERS['root'] == '/root'
        assert PATH_PLACEHOLDERS['videos'] == '/videos'
        assert 'sdcard' not in PATH_PLACEHOLDERS
        assert 'invalid' not in PATH_PLACEHOLDERS

    def test_add_common_storage_paths_without_plyer(self):
        with (patch.dict(sys.modules, {'plyer': None}),
              patch('ae.paths.os_platform', 'other')):
            add_common_storage_paths()

    def test_add_common_storage_paths_plyer_getter_exception(self):
        storage_path = types.SimpleNamespace(
            get_good_dir=lambda: '/good',
            get_bad_dir=lambda: (_ for _ in ()).throw(RuntimeError()),
        )
        mock_plyer = types.ModuleType('plyer')
        mock_plyer.storagepath = storage_path

        with (patch.dict(sys.modules, {'plyer': mock_plyer}),
              patch('ae.paths.os_platform', 'other')):
            add_common_storage_paths()

        assert PATH_PLACEHOLDERS['good'] == '/good'
        assert 'bad' not in PATH_PLACEHOLDERS

    def test_add_common_storage_paths_linux(self):
        with (patch('ae.paths.os_platform', 'linux'),
              patch('ae.paths.os_path_isdir', return_value=True),
              patch('ae.paths.os.walk', return_value=iter([
                  ('/mnt', ['drive1', 'drive2'], []), 
                  ('/media', ['drive3'], []),
              ]))):
            add_common_storage_paths()

        assert PATH_PLACEHOLDERS['drive1'] == '/mnt/drive1'
        assert PATH_PLACEHOLDERS['drive2'] == '/mnt/drive2'
        assert PATH_PLACEHOLDERS['drive3'] == '/media/drive3'

    def test_add_common_storage_paths_linux_without_directory(self):
        with (patch('ae.paths.os_platform', 'linux'),
              patch('ae.paths.os_path_isdir', return_value=False)):
            add_common_storage_paths()

    def test_add_common_storage_paths_apple(self):
        with (patch('ae.paths.os_platform', 'darwin'),
              patch('ae.paths.os_path_isdir', return_value=True),
              patch('ae.paths.os.walk', return_value=iter([('/Volume', ['disk1', 'disk2'], [])]))):
            add_common_storage_paths()

        assert PATH_PLACEHOLDERS['disk1'] == '/Volume/disk1'
        assert PATH_PLACEHOLDERS['disk2'] == '/Volume/disk2'

    def test_add_common_storage_paths_ios_without_volume(self):
        with (patch('ae.paths.os_platform', 'ios'),
              patch('ae.paths.os_path_isdir', return_value=False)):
            add_common_storage_paths()

    def test_add_common_storage_paths_windows(self):
        kernel32 = MagicMock()
        kernel32.GetLogicalDrives.return_value = 1
        kernel32.GetVolumeInformationW.side_effect = (lambda drive, name, *_args: setattr(name, 'value', 'TestDrive'))

        windll = MagicMock(kernel32=kernel32)
        ctypes = types.ModuleType('ctypes')
        ctypes.windll = windll
        ctypes.create_unicode_buffer = create_unicode_buffer

        with (patch('ae.paths.os_platform', 'win32'),
              patch.dict(sys.modules, {'ctypes': ctypes}),
              patch('ae.paths.os_path_isdir', return_value=True)):
            add_common_storage_paths()

        assert PATH_PLACEHOLDERS['TestDrive'] == 'A:/'

    def test_add_common_storage_paths_cygwin(self):
        with (patch('ae.paths.os_platform', 'cygwin'),
              patch.dict(sys.modules, {'ctypes': None})):
            add_common_storage_paths()

    def test_add_common_storage_paths_windows_without_drive(self):
        kernel32 = MagicMock()
        kernel32.GetLogicalDrives.return_value = 1

        windll = MagicMock(kernel32=kernel32)
        ctypes = types.ModuleType('ctypes')
        ctypes.windll = windll
        ctypes.create_unicode_buffer = create_unicode_buffer

        with (patch('ae.paths.os_platform', 'win32'),
              patch.dict(sys.modules, {'ctypes': ctypes}),
              patch('ae.paths.os_path_isdir', return_value=False)):
            add_common_storage_paths()


class TestAppPaths:
    def test_app_data_path(self):
        assert app_data_path()
        assert app_data_path().endswith(app_name_guess())
        assert app_data_path().startswith(user_data_path())

    def test_app_data_path_placeholder(self):
        assert 'app' in PATH_PLACEHOLDERS

    def test_app_docs_path(self):
        assert app_docs_path()
        assert app_docs_path().endswith(app_name_guess())
        assert app_docs_path().startswith(user_docs_path())

    def test_app_docs_path_placeholder(self):
        assert 'ado' in PATH_PLACEHOLDERS

    def test_app_name_placeholder(self):
        assert 'app_name' in PATH_PLACEHOLDERS

    def test_app_i18n_resources_folder_placeholder(self):
        assert 'loc' in PATH_PLACEHOLDERS

    def test_app_image_resources_folder_placeholder(self):
        assert 'img' in PATH_PLACEHOLDERS

    def test_app_sound_resources_folder_placeholder(self):
        assert 'snd' in PATH_PLACEHOLDERS

    def test_resources_folder_names(self):
        assert resources_folder_names() == list(RESOURCES_NAMES)
        assert resources_folder_names(resource_types={I18N_FOLDER}) == [I18N_FOLDER]
        assert resources_folder_names(resource_types=[IMAGE_FOLDER]) == [IMAGE_FOLDER]
        assert resources_folder_names(resource_types={SOUND_FOLDER: "any"}) == [SOUND_FOLDER]
        assert resources_folder_names(resource_types=RESOURCES_NAMES[1:]) == list(RESOURCES_NAMES[1:])

        assert resources_folder_names(path_placeholders=PATH_PLACEHOLDERS) == list(RESOURCES_NAMES)
        assert resources_folder_names(path_placeholders={I18N_FOLDER: 'tstDir'}) == ['tstDir'] + list(RESOURCES_NAMES)

        assert resources_folder_names(resource_types=[I18N_FOLDER], path_placeholders={"tst": "tst"}) == [I18N_FOLDER]


class TestCollector:
    def test_add_placeholder(self):
        coll = Collector(app="tst_app_path", main_app_name="tst_app_name")

        assert not coll.error_message
        assert "app" in coll.placeholders
        assert coll.placeholders["app"] == "tst_app_path"
        assert coll.placeholders["main_app_name"] == "tst_app_name"

    def test_collect_append_duplicates(self):
        coll = Collector(app='ae', tst=TST_TMP_ROOT)
        coll.collect("{app}", 'ae', "", append=("{app_name}", "paths" + '.py', "", 'ae'))

        assert not coll.error_message
        assert not coll.paths       # 'ae' not in coll.paths because the prefix of ae/paths.py gets found before ""/ae
        assert coll.files == [TST_MODULE, TST_MODULE]
        assert not coll.selected
        assert coll.failed == 0

    def test_collect_appends(self):
        coll = Collector(item_collector=coll_items, app='ae', tst=TST_TMP_ROOT)
        coll.collect("{app}", 'ae', "", append=("{app_name}", "paths" + '.py', "", 'ae'))

        assert not coll.error_message
        assert coll.paths == ['ae', 'ae', ".", 'ae']
        assert coll.files == [TST_MODULE, TST_MODULE]
        assert not coll.selected
        assert coll.failed == 0

    def test_collect_append_string(self):
        # noinspection PyArgumentEqualDefault
        coll = Collector(item_collector=coll_files, app='ae', tst=TST_TMP_ROOT, main_app_name=__file__)
        coll.collect("{app}", 'ae', "", append="{main_app_name}")

        assert not coll.error_message
        assert not coll.paths
        assert len(coll.files) == 1       # ["{cwd}/tests/test_paths" + '.py']
        assert coll.files[0].endswith(f"/ae_paths/{TST_TESTS_MODULE}")
        assert not coll.selected
        assert coll.failed == 0

    def test_collect_append_tests_files(self):
        coll = Collector()
        coll.collect("", append=TST_TMP_ROOT)

        assert not coll.error_message
        assert coll.paths == []

        coll.collect(TST_FOLDER_TESTS, append="*" + '.py')

        assert not coll.error_message
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES)

        coll.collect("", append=os_path_join(TST_FOLDER_TESTS, "*" + '.py'))

        assert not coll.error_message
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)

        coll.collect(TST_FOLDER_TESTS)

        assert coll.error_message
        assert coll.failed == 1
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == []

        coll.failed = 0
        coll.collect(TST_FOLDER_TESTS, append="")

        assert not coll.error_message
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == []

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'), append="")

        assert not coll.error_message
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 3)
        assert sorted(coll.selected) == []
        assert coll.failed == 0
        assert dict(coll.prefix_failed) == {TST_FOLDER_TESTS: 1}
        assert dict(coll.suffix_failed) == {'': 1}

    def test_collect_append_in_tests(self):
        coll = Collector(item_collector=coll_folders)
        coll.collect("", append=TST_FOLDER_TESTS)

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS]

        coll.collect(TST_FOLDER_TESTS, append="*" + '.py')

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == []

        coll.collect("", append=os_path_join(TST_FOLDER_TESTS, "*" + '.py'))

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == []

        coll.collect(TST_FOLDER_TESTS)

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS] * 2
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect(TST_FOLDER_TESTS, append="")

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS] * 3
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'), append="")

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS] * 3
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]
        assert coll.failed == 0
        assert dict(coll.prefix_failed) == {}
        assert coll.suffix_failed == {}

    def test_collect_append_tests_items(self):
        coll = Collector(item_collector=coll_items)
        coll.collect("", append=TST_FOLDER_TESTS)

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS]

        coll.collect(TST_FOLDER_TESTS, append="*" + '.py')

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES)

        coll.collect('', append=os_path_join(TST_FOLDER_TESTS, "*" + '.py'))

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)

        coll.collect(TST_FOLDER_TESTS)

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS] * 2
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect(TST_FOLDER_TESTS, append="")

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS] * 3
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'), append="")

        assert not coll.error_message
        assert coll.paths == [TST_FOLDER_TESTS] * 3
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 3)
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]
        assert coll.failed == 0
        assert dict(coll.prefix_failed) == {}
        assert coll.suffix_failed == {}

    def test_collect_deeper_py_files(self):
        sub_py_files1 = ["sub_dir/tst_sub_file" + '.py']
        sub_py_files2 = ["sub_dir/sub_dir2/tst_sub_sub_file" + '.py']
        sub_py_files3 = [TST_MODULE] + TST_TESTS_PY_FILES + sub_py_files1

        try:  # additional temp sub-dirs/-files in project root
            os.mkdir("sub_dir")
            for fn in sub_py_files1 + ["sub_dir/tst_sub_wo_extension"]:
                write_file(fn, f"file_content of sub {fn}")
            os.mkdir("sub_dir/sub_dir2")
            for fn in sub_py_files2 + ["sub_dir/sub_dir2/tst_sub_sub_wo_extension"]:
                write_file(fn, f"file_content of sub sub {fn}")

            coll = Collector()
            coll.collect("*" + '.py')
            assert coll.files == [TST_SETUP]

            coll = Collector()
            coll.collect("", append="*" + '.py')
            assert coll.files == [TST_SETUP]

            coll = Collector()
            coll.collect("**", append="*" + '.py')
            assert sorted(coll.files) == sorted([TST_SETUP] + sub_py_files3 + sub_py_files2)

            coll = Collector()
            coll.collect("*", append="*" + '.py')
            assert sorted(coll.files) == sorted(sub_py_files3)

            coll = Collector()
            coll.collect("*/*", append="*" + '.py')
            assert sorted(coll.files) == sub_py_files2

            coll = Collector()
            coll.collect("*/*/*", append="*" + '.py')
            assert sorted(coll.files) == []

            coll = Collector()
            coll.collect("**/*", append="*" + '.py')
            assert sorted(coll.files) == sorted(sub_py_files3 + sub_py_files2)

            coll = Collector()
            coll.collect("*/**", append="*" + '.py')
            assert sorted(coll.files) == sorted(sub_py_files3 + sub_py_files2)

            assert not coll.error_message
            assert coll.failed == 0
        finally:
            if os_path_isdir("sub_dir"):
                shutil.rmtree("sub_dir")

    def test_collect_no_args(self):
        coll = Collector()
        coll.collect()

        assert not coll.error_message
        assert not coll.paths
        assert not coll.files
        assert not coll.selected
        assert coll.failed == 0
        assert len(coll.prefix_failed) == 0
        assert len(coll.suffix_failed) == 0

    def test_collect_nothing_findable(self):
        coll = Collector(app="tst_app_path")
        prefixes = ("{cwd}/../..", "{app}", "{usr}", "{usr}/{app_name}", "{cwd}/..", "{cwd}", )
        coll.collect(*prefixes, append=("not : valid fil nam", "not_______existent_ tst file name.ext", ))

        assert not coll.error_message
        assert not coll.paths
        assert not coll.files
        assert not coll.selected
        assert coll.failed == 0
        assert not coll.prefix_failed
        assert len(coll.prefix_failed) == 0
        assert len(coll.suffix_failed) == 0

    def test_collect_prefixes_as_relative_and_duplicate_absolute_folder_paths(self):
        coll = Collector(item_collector=coll_folders, app='ae', usr='ae')
        coll.collect('{app}', '{cwd}', '{usr}')

        assert not coll.error_message
        # assert coll.paths == ['ae', "/home/andi/src/ae_paths", 'ae'] != CI: ['ae', "/builds/ae-group/ae_paths", 'ae']
        assert coll.paths == ['ae', normalize('{cwd}'), 'ae']
        assert not coll.files
        assert coll.selected == ['ae', normalize('{cwd}'), 'ae']
        assert coll.failed == 0

    def test_collect_prefixes_only(self):
        coll = Collector(item_collector=coll_folders, app='ae', usr=TST_TMP_ROOT)
        coll.collect("{app}", "{usr}")

        assert not coll.error_message
        assert len(coll.paths) == 2
        assert 'ae' in coll.paths
        assert TST_TMP_ROOT in coll.paths
        assert coll.files == []
        assert coll.selected == coll.paths + coll.files
        assert coll.failed == 0

    def test_collect_select_failures(self):
        coll = Collector(cw=os.getcwd(), app='ae', tst=TST_TMP_ROOT)
        coll.collect("{cw}", "{app}", 'ae', select=".*")

        assert coll.error_message
        assert not coll.paths
        assert 2 <= len(coll.files) <= 5
        # ["{cw}/.gitignore", "{cw}/.commit_msg.txt", "{cw}/.python-version", "{cw}/.gitlab-ci.yml", "{cw}/.coverage"]
        assert all(_.startswith(os.getcwd()) for _ in coll.files)
        files = [os_path_basename(_) for _ in coll.files]
        assert '.gitignore' in files
        assert '.gitlab-ci.yml' in files
        assert coll.selected == coll.files
        assert coll.failed == 2
        assert coll.prefix_failed == {"{app}": 1, 'ae': 1}
        assert coll.suffix_failed == {".*": 2}

    def test_collect_selects(self):
        coll = Collector(item_collector=coll_items, app='ae', tst=TST_TMP_ROOT)
        coll.collect("{cwd}", "{app}", 'ae',
                     select=(".*", "README.md", TST_TESTS_MODULE, "", 'ae',))

        assert len(coll.paths) >= 4   # ["{cwd}", "{cwd}/ae", 'ae', 'ae'] + localMachFolders .git/.pylint/.mypy_cache/..
        assert sum(1 for _ in coll.paths if _ == os.getcwd()) == 1
        assert sum(1 for _ in coll.paths if _ == os_path_join(os.getcwd(), 'ae')) == 1
        assert sum(1 for _ in coll.paths if _ == 'ae') == 2

        assert 4 <= len(coll.files) <= 7    # .commit_msg.txt,d .python-version and .coverage are missing on CI host
        # ["{cwd}/.gitignore", "{cwd}/.commit_msg.txt", "{cwd}/.python-version", "{cwd}/.gitlab-ci.yml",
        #  "{cwd}/README.md", "{cwd}/tests/test_paths" + '.py']
        assert all(_.startswith(os.getcwd()) for _ in coll.files)
        files = [os_path_basename(_) for _ in coll.files]
        assert '.gitignore' in files
        assert '.gitlab-ci.yml' in files
        assert 'README.md' in files
        assert 'test_paths' + '.py' in files

        assert all(_ in coll.files or _ in coll.paths for _ in coll.selected)
        assert 0 < coll.failed < len(coll.paths) + len(coll.files)
        assert coll.error_message

    def test_collect_select_string(self):
        coll = Collector(app='ae', tst=TST_TMP_ROOT)
        coll.collect("{cwd}", "{app}", 'ae', select=".*")
        assert not coll.paths
        assert 2 <= len(coll.files) <= 5
        # ["{cwd}/.gitignore", "{cwd}/.gitlab-ci.yml"] only .commit_msg.txt|.python-version|.coverage are not at CI host
        assert all(_.startswith(os.getcwd()) for _ in coll.files)
        files = [os_path_basename(_) for _ in coll.files]
        assert '.gitignore' in files
        assert '.gitlab-ci.yml' in files
        assert coll.selected == coll.files
        assert 0 < coll.failed <= len(coll.paths) + len(coll.files)  # failed == 2 from {app}.*|ae.* == ae.*|ae.*
        assert coll.error_message

    def test_collect_select_tests_files(self):
        coll = Collector()      # item_collector=coll_files is the default argument
        coll.collect("", select=TST_FOLDER_TESTS)
        assert coll.paths == []
        assert sorted(coll.selected) == []

        coll.collect(TST_FOLDER_TESTS, select="*" + '.py')
        assert coll.paths == []
        assert sorted(coll.files) == TST_TESTS_PY_FILES
        assert sorted(coll.selected) == TST_TESTS_PY_FILES

        coll.collect("", select=os_path_join(TST_FOLDER_TESTS, "*" + '.py'))
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == sorted(TST_TESTS_PY_FILES * 2)

        coll.collect(TST_FOLDER_TESTS, select="")
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == sorted(TST_TESTS_PY_FILES * 2)

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'))      # collect select kwarg defaults to ""
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 3)
        assert sorted(coll.selected) == sorted(TST_TESTS_PY_FILES * 3)

        assert coll.failed == 2
        assert coll.error_message
        assert dict(coll.prefix_failed) == {"": 1, TST_FOLDER_TESTS: 1}
        assert dict(coll.suffix_failed) == {"": 1, TST_FOLDER_TESTS: 1}

    def test_collect_select_in_tests(self):
        coll = Collector(item_collector=coll_folders)
        coll.collect("", select=TST_FOLDER_TESTS)
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect(TST_FOLDER_TESTS, select="*" + '.py')
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect("", select=os_path_join(TST_FOLDER_TESTS, "*" + '.py'))
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == sorted([TST_FOLDER_TESTS])

        coll.collect(TST_FOLDER_TESTS, select="")
        assert coll.paths == [TST_FOLDER_TESTS] * 2
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == sorted([TST_FOLDER_TESTS] * 2)

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'))      # collect select kwarg defaults to ""
        assert coll.paths == [TST_FOLDER_TESTS] * 2
        assert sorted(coll.files) == []
        assert sorted(coll.selected) == sorted([TST_FOLDER_TESTS] * 2)

        assert coll.failed == 3
        assert coll.error_message
        assert dict(coll.prefix_failed) == {"": 1, os_path_join(TST_FOLDER_TESTS, "*" + '.py'): 1, TST_FOLDER_TESTS: 1}
        assert dict(coll.suffix_failed) == {"": 1, os_path_join(TST_FOLDER_TESTS, "*" + '.py'): 1, "*" + '.py': 1}

    def test_collect_select_tests_items(self):
        coll = Collector(item_collector=coll_items)
        coll.collect("", select=TST_FOLDER_TESTS)
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.selected) == [TST_FOLDER_TESTS]

        coll.collect(TST_FOLDER_TESTS, select="*" + '.py')
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == TST_TESTS_PY_FILES
        assert sorted(coll.selected) == [TST_FOLDER_TESTS] + TST_TESTS_PY_FILES

        coll.collect("", select=os_path_join(TST_FOLDER_TESTS, "*" + '.py'))
        assert coll.paths == [TST_FOLDER_TESTS]
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == sorted([TST_FOLDER_TESTS] + TST_TESTS_PY_FILES * 2)

        coll.collect(TST_FOLDER_TESTS, select="")
        assert coll.paths == [TST_FOLDER_TESTS] * 2
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 2)
        assert sorted(coll.selected) == sorted([TST_FOLDER_TESTS] * 2 + TST_TESTS_PY_FILES * 2)

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'))      # collect select kwarg defaults to ""
        assert coll.paths == [TST_FOLDER_TESTS] * 2
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES * 3)
        assert sorted(coll.selected) == sorted([TST_FOLDER_TESTS] * 2 + TST_TESTS_PY_FILES * 3)

        assert coll.failed == 0
        assert not coll.error_message
        assert dict(coll.prefix_failed) == {}
        assert coll.suffix_failed == {}

    def test_collect_simplest(self):
        coll = Collector()  # item_collector=coll_files is the default argument -> no paths will be collected
        coll.collect(TST_TMP_ROOT)
        assert coll.paths == []
        assert coll.files == []

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*"))
        assert coll.paths == []
        assert sorted(coll.files) == sorted(TST_TESTS_PY_FILES + [TST_TESTS_REQS_PATH])

        coll.collect(os_path_join(TST_FOLDER_TESTS, "*" + '.py'))
        coll.collect(os_path_join(TST_FOLDER_TESTS, "*.txt"))
        assert coll.paths == []
        assert sorted(coll.files) == sorted(2 * (TST_TESTS_PY_FILES + [TST_TESTS_REQS_PATH]))


class TestCopyFiles:
    def test_blocked_copy_to_parent_dir(self, tst_move_files):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = os_path_join(src_dir, "..")
        dst_block_file = os_path_join(dst_dir, TST_INI_FILE)
        write_file_text(TST_OLD_CONTENT, dst_block_file)
        assert os_path_isfile(dst_block_file)
        for src_file_path in tst_move_files:
            assert os_path_isfile(src_file_path)
            dst_file = os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os_path_isfile(dst_file)
        tst_overwrite = (TST_OVER_FOLDER_NAME in src_dir)

        copy_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            assert os_path_isfile(tst_move_files[0])
            assert read_file_text(tst_move_files[0]) == TST_FILE_CONTENT
            dst_file = os_path_join(dst_dir, os_path_relpath(tst_move_files[0], src_dir))
            assert os_path_isfile(dst_file)
            assert read_file_text(dst_file) == TST_OLD_CONTENT

            assert os_path_isfile(tst_move_files[1])
            dst_file = os_path_join(dst_dir, os_path_relpath(tst_move_files[1], src_dir))
            assert os_path_isfile(dst_file)
            assert read_file_text(dst_file) == TST_NEW_CONTENT

    def test_copy_to_parent_dir(self, tst_move_files):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = os_path_join(src_dir, "..")
        for src_file_path in tst_move_files:
            assert os_path_isfile(src_file_path)
            assert not os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))
            assert not os_path_isdir(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))
        tst_overwrite = (TST_OVER_FOLDER_NAME in src_dir)

        copy_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            for src_file_path in tst_move_files:
                assert os_path_isfile(src_file_path)
                assert os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))


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

    def test_add_path_init(self, tst_prop_files):
        wop, wip = tst_prop_files
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        assert len(fr) == 1
        assert TST_PROP_FILE in fr
        files = fr[TST_PROP_FILE]
        assert len(files) == 2
        assert all(_.path in (wop, wip) for _ in files)
        assert all(_.stem == TST_PROP_FILE for _ in files)
        assert all(_.ext == TST_PROP_EXT for _ in files)
        assert all(_.properties in ({}, TST_PROPERTIES) for _ in files)

    def test_add_path_redirect(self, tst_prop_files):
        wop, wip = tst_prop_files
        fri = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        fr = FilesRegister()
        assert len(fr.add_paths(os_path_join(TST_PROP_ROOT, "**"))) == len(tst_prop_files)
        assert len(fri) == len(fr)
        assert TST_PROP_FILE in fr
        files = fr[TST_PROP_FILE]
        assert len(files) == len(tst_prop_files)
        assert all(_.path in (wop, wip) for _ in files)
        assert all(_.stem == TST_PROP_FILE for _ in files)
        assert all(_.ext == TST_PROP_EXT for _ in files)
        assert all(_.properties in ({}, TST_PROPERTIES) for _ in files)

        old_len = len(fr)
        assert 'test_files' not in fr
        fr.add_file(os_path_join(TST_TMP_ROOT, 'test_files' + '.py'))
        assert old_len < len(fr)
        assert 'test_files' in fr

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

    def test_cache_file_class(self, tst_prop_files):
        wop, wip = tst_prop_files
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"), file_class=CachedFile, object_loader=tst_file_loader)
        assert len(fr) == 1
        assert TST_PROP_FILE in fr
        files = fr[TST_PROP_FILE]
        assert len(files) == 2
        assert all(_.path in (wop, wip) for _ in files)
        assert all(_.stem == TST_PROP_FILE for _ in files)
        assert all(_.ext == TST_PROP_EXT for _ in files)
        assert all(_.properties in ({}, TST_PROPERTIES) for _ in files)

        assert all(isinstance(_, CachedFile) for _ in files)

    def test_call_find_file_redirect(self, tst_prop_files):
        assert TST_PROP_FILE in tst_prop_files[1]
        fr = FilesRegister(TST_PROP_ROOT)
        assert fr(TST_PROP_FILE, properties=TST_PROPERTIES) == fr.find_file(TST_PROP_FILE, properties=TST_PROPERTIES)

    def test_find_file_by_name(self, tst_prop_files):
        assert TST_PROP_FILE in tst_prop_files[1]
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        assert isinstance(fr, FilesRegister)
        ff = fr.find_file(TST_PROP_FILE)
        assert isinstance(ff, RegisteredFile)
        assert ff.stem == TST_PROP_FILE

    def test_find_file_by_properties(self, tst_prop_files):
        assert TST_PROP_FILE in tst_prop_files[1]
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        ff = fr.find_file(TST_PROP_FILE, properties=TST_PROPERTIES)
        assert isinstance(ff, RegisteredFile)
        assert ff.stem == TST_PROP_FILE
        assert ff.properties == TST_PROPERTIES

    def test_find_file_by_property_matcher(self, tst_prop_files):
        assert TST_PROP_FILE in tst_prop_files[1]
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        # noinspection PyTypeChecker
        ff = fr.find_file(TST_PROP_FILE, property_matcher=tst_property_matcher)
        assert isinstance(ff, RegisteredFile)
        assert ff.stem == TST_PROP_FILE
        assert ff.properties == TST_PROPERTIES

    def test_find_file_by_property_matcher_and_file_sorter(self, tst_prop_files):
        assert TST_PROP_FILE in tst_prop_files[1]
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        # noinspection PyTypeChecker
        ff = fr.find_file(TST_PROP_FILE, properties=TST_PROPERTIES, file_sorter=tst_file_sorter)
        assert isinstance(ff, RegisteredFile)
        assert ff.stem == TST_PROP_FILE
        assert ff.properties == TST_PROPERTIES

    def test_find_file_by_sorter(self, tst_prop_files):
        assert TST_PROP_FILE in tst_prop_files[1]
        fr = FilesRegister(os_path_join(TST_PROP_ROOT, "**"))
        # noinspection PyTypeChecker
        ff = fr.find_file(TST_PROP_FILE, file_sorter=tst_file_sorter)
        assert isinstance(ff, RegisteredFile)
        assert ff.stem == TST_PROP_FILE
        assert ff.properties == {}      # finds the one without properties because int-default==0

    def test_find_file_with_default_file_sorter(self):
        # noinspection PyTypeChecker
        fr = FilesRegister(file_sorter=tst_file_sorter)
        assert fr.file_sorter is tst_file_sorter

    def test_find_file_with_default_property_matcher(self):
        # noinspection PyTypeChecker
        fr = FilesRegister(property_matcher=tst_property_matcher)
        assert fr.property_watcher is tst_property_matcher

    def test_init_file_sorter(self):
        # noinspection PyTypeChecker
        fr = FilesRegister(file_sorter=tst_file_sorter)
        assert fr.file_sorter is tst_file_sorter

    def test_init_min(self):
        fr = FilesRegister()
        assert not fr.property_watcher
        assert not fr.file_sorter
        assert not fr.keys()
        assert not fr.values()

    def test_init_property_matcher(self):
        # noinspection PyTypeChecker
        fr = FilesRegister(property_matcher=tst_property_matcher)
        assert fr.property_watcher is tst_property_matcher

    def test_reclassify(self):
        fr = FilesRegister()
        fr.add_file('ttt')
        fr.add_file("dir/ttt")
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


class TestOtherHelpers:
    def test_coll_item_type(self):
        assert coll_item_type(TST_FOLDER_TESTS) is UNSET
        assert coll_item_type(TST_TESTS_MODULE) == '.py'
        assert coll_item_type("not existing file.txt") is None

        with patch('ae.paths.os_path_isfile', return_value=True):
            assert coll_item_type("mocked_existing_file_without_extension") == ""  # old version with splitext == "."

    def test_path_join(self):
        assert path_join("") == os_path_join("")
        assert path_join('part') == os_path_join('part')
        assert path_join('part', 'part2') == os_path_join('part', 'part2')
        assert path_join('part', '', 'part2') == os_path_join('part', '', 'part2')
        assert path_join('part', ".", 'part2') == os_path_join('part', ".", 'part2')
        assert path_join('part', "..", 'part2') == os_path_join('part', "..", 'part2')
        assert path_join('part', "/part2") == os_path_join('part', "/part2")
        assert path_join('part', "/", 'part2') == os_path_join('part', "/", 'part2')
        assert path_join('part', "//", 'part2') == os_path_join('part', "//", 'part2')
        assert path_join("/part", 'part2') == os_path_join("/part", 'part2')
        assert path_join('', 'part2') == os_path_join('', 'part2')

        assert path_join('part', '') == 'part'  # os_path_join() returns "part/" in this case
        assert path_join('part', '') != os_path_join('part', '')

    def test_path_match(self):
        assert path_match('c' + '.py', "?" + '.py')
        assert path_match('c' + '.py', "?.p?")
        assert not path_match('c' + '.py', "??.p?")
        assert not path_match('c' + '.py', "?.p??")

        assert path_match('c' + '.py', "*")
        assert path_match('c' + '.py', "*" + '.py')
        assert path_match('c' + '.py', "c" + '.py')

        assert path_match('c' + '.py', "**/*" + '.py')
        assert path_match("a/b/c" + '.py', "**/*" + '.py')
        assert path_match("/a/b/c" + '.py', "**/*" + '.py')
        assert path_match("a/b/c" + '.py', "a/**")
        assert path_match("/a/b/c" + '.py', "/a/**")
        assert path_match("a/b/c" + '.py', "a/**/b/**")
        assert path_match("/a/b/c" + '.py', "/a/**/b/**")
        assert path_match("a/b/c" + '.py', "a/**/b/**/c.*")
        assert path_match("/a/b/c" + '.py', "/a/**/b/**/c.*")
        assert not path_match("a/b/c" + '.py', "a/*")
        assert not path_match("/a/b/c" + '.py', "a/*")
        assert not path_match("a/b/c" + '.py', "a**/*" + '.py')
        assert not path_match("/a/b/c" + '.py', "a**/*" + '.py')
        assert not path_match("a/b/c" + '.py', "/a/**")
        assert not path_match("/a/b/c" + '.py', "a/**")

        assert path_match('abc' + '.py', "[axy]bc" + '.py')
        assert path_match('abc' + '.py', "ab[cxy]" + '.py')
        assert path_match('abc' + '.py', "ab[!dxy]" + '.py')

    def test_path_match_py313(self):
        with (patch('ae.paths.sys.version_info', (3, 13)),
              patch('ae.paths.PurePath') as mock_full_match):
            assert path_match('c' + '.py', "?" + '.py')

        mock_full_match.assert_called_once_with('c' + '.py')
        mock_full_match.return_value.full_match.assert_called_once_with('?' + '.py')

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

    def test_paths_match(self):
        assert list(paths_match(['c' + '.py'], ["**/*" + '.py'])) == ['c' + '.py']
        assert list(paths_match(['a' + '.py', "a/b/c.d"], ["**/*" + '.py'])) == ['a' + '.py']
        assert set(paths_match(['a' + '.py', "a/b/c" + '.py'], ["**/*" + '.py'])) == {'a' + '.py', "a/b/c" + '.py'}
        assert list(paths_match(['c' + '.py'], ["**/*" + '.py', 'file.name'])) == ['c' + '.py']
        assert list(paths_match(['file.name', 'x.y'], ["**/*.d", 'file.name'])) == ['file.name']
        assert list(paths_match(['c' + '.py'], ["**/*.d", 'file.name'])) == []

    def test_relative_file_paths(self):
        assert relative_file_paths("", []) == set()
        assert not relative_file_paths("", [])
        assert not relative_file_paths("", ['NonExistingPackageName'])

        files = relative_file_paths("", ["*"])

        assert files
        assert TST_SETUP in files
        assert not any("/" in _.replace("\\", "/") for _ in files)
        assert not any(_.startswith(".") for _ in files)

        files = relative_file_paths("", [".*"])

        assert files
        assert '.gitignore' in files
        assert not any("/" in _.replace("\\", "/") for _ in files)
        assert all(_.startswith(".") for _ in files)

        files = relative_file_paths("", [os_path_join("**", "*" + '.py')])

        assert files == {TST_SETUP, TST_TESTS_MODULE, TST_TESTS_CONF_PATH, TST_MODULE}

        assert files == relative_file_paths("", [os_path_join("**", "*")], skip_file_path=lambda fp: fp[-3:] != '.py')

    def test_skip_py_cache_files(self):
        assert skip_py_cache_files('__pycache__')
        assert skip_py_cache_files(f"a/c/c/{'__pycache__'}")
        assert skip_py_cache_files(f"/a/c/c/{'__pycache__'}")
        assert skip_py_cache_files(f"a/c/c/{'__pycache__'}/.")
        assert skip_py_cache_files(f"a/c/c/{'__pycache__'}/x" + '.py')


class TestMoveFiles:
    def test_blocked_moves_to_parent_dir(self, tst_move_files):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = os_path_join(src_dir, "..")
        dst_block_file = os_path_join(dst_dir, TST_INI_FILE)
        write_file_text(TST_OLD_CONTENT, dst_block_file)
        assert os_path_isfile(dst_block_file)
        for src_file_path in tst_move_files:
            assert os_path_isfile(src_file_path)
            dst_file = os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os_path_isfile(dst_file)
        tst_overwrite = (TST_OVER_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            assert os_path_isfile(tst_move_files[0])
            assert read_file_text(tst_move_files[0]) == TST_FILE_CONTENT
            dst_file = os_path_join(dst_dir, os_path_relpath(tst_move_files[0], src_dir))
            assert os_path_isfile(dst_file)
            assert read_file_text(dst_file) == TST_OLD_CONTENT

            assert not os_path_isfile(tst_move_files[1])
            dst_file = os_path_join(dst_dir, os_path_relpath(tst_move_files[1], src_dir))
            assert os_path_isfile(dst_file)
            assert read_file_text(dst_file) == TST_NEW_CONTENT

    def test_file_moves_to_user_dir_via_check_all(self, monkeypatch, tst_move_files, tmp_path):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = str(tmp_path)
        monkeypatch.setitem(PATH_PLACEHOLDERS, 'usr', dst_dir)

        moved = move_files(src_dir, "{usr}")

        assert moved
        for src_file_path in tst_move_files:
            assert not os_path_isfile(src_file_path) and not os_path_isdir(src_file_path)
            assert os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))

    def test_moves_to_parent_dir(self, tst_move_files):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = os_path_join(src_dir, "..")
        for src_file_path in tst_move_files:
            assert os_path_isfile(src_file_path)
            assert not os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))
            assert not os_path_isdir(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))
        tst_overwrite = (TST_OVER_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if not tst_overwrite:
            for src_file_path in tst_move_files:
                assert not os_path_isfile(src_file_path) and not os_path_isdir(tst_move_files[0])
                assert os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))

    def test_overwrites_to_parent_dir(self, tst_move_files):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = os_path_join(src_dir, "..")
        for src_file_path in tst_move_files:
            assert os_path_isfile(src_file_path)
            assert not os_path_isdir(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))
            assert not os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))
        tst_overwrite = (TST_OVER_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if tst_overwrite:
            for src_file_path in tst_move_files:
                assert not os_path_isfile(src_file_path) and not os_path_isdir(tst_move_files[0])
                assert os_path_isfile(os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir)))

    def test_unblocked_overwrites_to_parent_dir(self, tst_move_files):
        src_dir = os_path_dirname(tst_move_files[0])
        dst_dir = os_path_join(src_dir, "..")
        dst_block_file = os_path_join(dst_dir, TST_INI_FILE)
        write_file_text(TST_OLD_CONTENT, dst_block_file)
        assert os_path_isfile(dst_block_file)
        for src_file_path in tst_move_files:
            assert os_path_isfile(src_file_path)
            dst_file = os_path_join(dst_dir, os_path_relpath(src_file_path, src_dir))
            assert dst_file == dst_block_file or not os_path_isfile(dst_file)
        tst_overwrite = (TST_OVER_FOLDER_NAME in src_dir)

        move_files(src_dir, dst_dir, overwrite=tst_overwrite)

        if tst_overwrite:
            assert not os_path_isfile(tst_move_files[0]) and not os_path_isdir(tst_move_files[0])
            dst_file = os_path_join(dst_dir, os_path_relpath(tst_move_files[0], src_dir))
            assert os_path_isfile(dst_file)
            assert read_file_text(dst_file) == TST_FILE_CONTENT

            assert not os_path_isfile(tst_move_files[1])
            dst_file = os_path_join(dst_dir, os_path_relpath(tst_move_files[1], src_dir))
            assert os_path_isfile(dst_file)
            assert read_file_text(dst_file) == TST_NEW_CONTENT


class TestPathFiles:
    def test_file_callable(self):
        def add_file(f_name, **kwargs):
            """ callable used for the file_class argument of path_files. """
            added.append((f_name, kwargs))
            return f_name
        added = []
        found = path_files("**" + '.py', file_class=add_file, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == TST_SETUP
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_files. """
            def __init__(self, f_name, **kwargs):
                self.file_name = f_name
                self.stem = os_path_splitext(f_name)[0]
                added.append((f_name, kwargs))
        added = []
        found = path_files("*" + '.py', file_class=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].file_name == TST_SETUP
        assert found[0].stem == "setup"
        assert added[0][0] == found[0].file_name
        assert added[0][1] == dict(a=3, b=6)

    def test_non_recursive(self):
        assert path_files(TST_SETUP) == [TST_SETUP]
        assert path_files(TST_MODULE) == [TST_MODULE]
        assert path_files(TST_TESTS_MODULE) == [TST_TESTS_MODULE]

        assert path_files("../ae_paths") == []
        assert path_files("../ae_paths/" + TST_SETUP) == ["../ae_paths/" + TST_SETUP]

        assert path_files(".") == []
        assert path_files("./" + TST_SETUP) == ["./" + TST_SETUP]
        assert path_files("./" + TST_MODULE) == ["./" + TST_MODULE]

        assert path_files('ae') == []
        assert path_files(TST_MODULE) == [TST_MODULE]

        assert path_files(TST_TMP_ROOT) == []
        assert path_files(TST_TESTS_MODULE) == [TST_TESTS_MODULE]

    def test_path_lib(self):
        found = path_files("*" + '.py', file_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == TST_SETUP
        assert found[0].stem == "setup"

        found = path_files("*" + '.py', file_class=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == TST_SETUP
        assert found[0].stem == "setup"

    def test_placeholders(self):
        assert len(path_files("{cwd}")) == len(path_files("."))
        assert path_files("{cwd}/" + TST_MODULE)[0].endswith("/ae_paths/" + TST_MODULE)

        assert len(path_files("{cwd}/**/*" + '.py')) == 4  # ...setup.py, ...paths.py, ...test_paths.py, ...conftest.py
        assert all(_.endswith('.py') for _ in path_files("{cwd}/**/*" + '.py'))
        assert all(_.startswith("/") for _ in path_files("{cwd}/**/*" + '.py'))

    def test_wildcards(self):
        assert path_files("*" + '.py') == [TST_SETUP]
        assert path_files("**" + '.py') == [TST_SETUP]

        assert path_files("set??" + '.py') == [TST_SETUP]
        assert path_files("setup*" + '.py') == [TST_SETUP]
        assert path_files("setup**" + '.py') == [TST_SETUP]

        assert TST_MODULE in path_files("ae/**")
        assert path_files("ae/**/*" + '.py') == [TST_MODULE]
        assert path_files("**/pat?s" + '.py') == [TST_MODULE]

        assert len(path_files("**/*" + '.py')) == 4
        assert set(path_files("**/*" + '.py')) == {
            TST_SETUP, TST_MODULE, TST_TESTS_MODULE, TST_TESTS_CONF_PATH}

        assert path_files("{cwd}/**/paths" + '.py')[0].endswith("ae_paths/" + TST_MODULE)
        assert path_files("{cwd}/**/paths.?y")[0].endswith("ae_paths/" + TST_MODULE)

        assert len(path_files("{cwd}/**/*paths" + '.py')) == 2
        assert len(path_files("{cwd}/**/*paths.?y")) == 2

    def test_without_placeholders_and_wildcards(self):
        assert path_files(TST_SETUP) == [TST_SETUP]
        assert path_files(TST_MODULE) == [TST_MODULE]
        assert path_files(TST_TESTS_MODULE) == [TST_TESTS_MODULE]

        assert path_files("../ae_paths") == []
        assert path_files("../ae_paths/" + TST_SETUP) == ["../ae_paths/" + TST_SETUP]

        assert path_files(".") == []
        assert all(_[0] == "." for _ in path_files("."))
        assert path_files("./" + TST_SETUP) == ["./" + TST_SETUP]

        assert path_files('ae') == []
        assert TST_MODULE not in path_files('ae')        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_files(TST_MODULE) == [TST_MODULE]

        assert path_files(TST_TMP_ROOT) == []
        assert TST_TESTS_MODULE not in path_files(TST_TMP_ROOT)
        assert path_files(TST_TESTS_MODULE) == [TST_TESTS_MODULE]


class TestPathFolders:
    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_folders. """
            def __init__(self, f_name, **kwargs):
                self.folder_name = f_name
                self.stem = os_path_splitext(f_name)[0]
                added.append((f_name, kwargs))
        added = []
        found = path_folders(TST_TMP_ROOT, folder_class=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].folder_name == TST_TMP_ROOT
        assert found[0].stem == TST_TMP_ROOT
        assert added[0][0] == found[0].folder_name
        assert added[0][1] == dict(a=3, b=6)

    def test_folder_callable(self):
        def add_folder(folder_name, **kwargs):
            """ callable used for the file_class argument of path_folders. """
            added.append((folder_name, kwargs))
            return folder_name
        added = []
        found = path_folders(TST_TMP_ROOT, folder_class=add_folder, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == TST_TMP_ROOT
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_path_lib(self):
        found = path_folders(TST_TMP_ROOT, folder_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == os_path_basename(TST_TMP_ROOT)
        assert found[0].stem == os_path_basename(TST_TMP_ROOT)

        found = path_folders(TST_TMP_ROOT, folder_class=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == os_path_basename(TST_TMP_ROOT)
        assert found[0].stem == os_path_basename(TST_TMP_ROOT)

    def test_non_recursive(self):
        assert path_folders(TST_SETUP) == []
        assert path_folders(TST_MODULE) == []
        assert path_folders(TST_TESTS_MODULE) == []

        assert path_folders("../ae_paths") == ["../ae_paths"]
        assert path_folders("../ae_paths/" + TST_SETUP) == []

        assert path_folders(".") == ["."]
        assert path_folders("./" + TST_SETUP) == []
        assert path_folders("./" + TST_MODULE) == []

        assert path_folders('ae') == ['ae']
        assert path_folders(TST_MODULE) == []

        assert path_folders(TST_TMP_ROOT) == [TST_TMP_ROOT]
        assert path_folders(TST_TESTS_MODULE) == []

    def test_placeholders(self):
        assert len(path_folders("{cwd}")) == len(path_folders("."))
        assert path_folders("{cwd}/ae")[0].endswith("/ae_paths/ae")

        assert path_folders("{cwd}/**")
        assert any(_.endswith("/ae_paths/ae") for _ in path_folders("{cwd}/**"))
        assert any(_.endswith("/ae_paths/" + TST_FOLDER_TESTS) for _ in path_folders("{cwd}/**"))
        assert all(_.startswith("/") for _ in path_folders("{cwd}/**"))

    def test_wildcards(self):
        assert path_folders("*" + '.py') == []
        assert path_folders("**" + '.py') == []

        assert path_folders("set??" + '.py') == []
        assert path_folders("setup*" + '.py') == []
        assert path_folders("setup**" + '.py') == []

        assert "../ae_paths/ae" in path_folders("../ae_paths/**")
        assert "../ae_paths/ae/" in path_folders("../ae_paths/ae/**")

        assert path_folders("**")
        assert 'ae' in path_folders("**")
        assert TST_FOLDER_TESTS in path_folders("**")

        assert any(_.endswith("ae_paths/ae") for _ in path_folders("{cwd}/**"))
        assert any(_.endswith("ae_paths/ae/") for _ in path_folders("{cwd}/**/"))

    def test_without_placeholders_and_wildcards(self):
        assert path_folders(TST_SETUP) == []
        assert path_folders(TST_MODULE) == []
        assert path_folders(TST_TESTS_MODULE) == []

        assert path_folders("../ae_paths") == ["../ae_paths"]
        assert path_folders("../ae_paths/" + TST_SETUP) == []

        assert path_folders(".") == ["."]
        assert all(_[0] == "." for _ in path_folders("."))
        assert path_folders("./" + TST_SETUP) == []

        assert path_folders('ae') == ['ae']
        assert TST_MODULE not in path_folders('ae')        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_folders(TST_MODULE) == []

        assert path_folders(TST_TMP_ROOT) == [TST_TMP_ROOT]
        assert TST_TESTS_MODULE not in path_folders(TST_TMP_ROOT)
        assert path_folders(TST_TESTS_MODULE) == []


class TestPathItems:
    def test_file_callable(self):
        def add_file(f_name: str, **kwargs: Any) -> str:
            """ callable used for the file_class argument of path_files. """
            added.append((f_name, kwargs))
            return f_name
        added = []
        found = path_items("**" + '.py', creator=add_file, a=1, b=2)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0] == TST_SETUP
        assert added[0][0] == found[0]
        assert added[0][1] == dict(a=1, b=2)

    def test_file_class(self):
        class FileClass:
            """ class used for the file_class argument of path_files. """
            def __init__(self, f_name, **kwargs):
                self.file_name = f_name
                self.stem = os_path_splitext(f_name)[0]
                added.append((f_name, kwargs))
        added = []
        found = path_items("*" + '.py', creator=FileClass, a=3, b=6)

        assert len(found) == len(added)
        assert len(found) == 1
        assert found[0].file_name == TST_SETUP
        assert found[0].stem == "setup"
        assert added[0][0] == found[0].file_name
        assert added[0][1] == dict(a=3, b=6)

    def test_non_recursive(self):
        assert path_items(TST_SETUP) == [TST_SETUP]
        assert path_items(TST_MODULE) == [TST_MODULE]
        assert path_items(TST_TESTS_MODULE) == [TST_TESTS_MODULE]

        assert path_items("../ae_paths") == ["../ae_paths"]
        assert path_items("../ae_paths/" + TST_SETUP) == ["../ae_paths/" + TST_SETUP]

        assert path_items(".") == ["."]
        assert path_items("./" + TST_SETUP) == ["./" + TST_SETUP]
        assert path_items("./" + TST_MODULE) == ["./" + TST_MODULE]

        assert path_items('ae') == ['ae']
        assert path_items(TST_MODULE) == [TST_MODULE]

        assert path_items(TST_TMP_ROOT) == [TST_TMP_ROOT]
        assert path_items(TST_TESTS_MODULE) == [TST_TESTS_MODULE]

    def test_path_lib(self):
        found = path_files("*" + '.py', file_class=pathlib.PurePath)

        assert len(found) == 1
        assert found[0].name == TST_SETUP
        assert found[0].stem == "setup"

        found = path_items("*" + '.py', creator=pathlib.Path)

        assert len(found) == 1
        assert found[0].name == TST_SETUP
        assert found[0].stem == "setup"

    def test_placeholders(self):
        assert len(path_items("{cwd}")) == len(path_items("."))
        assert path_items("{cwd}/" + TST_MODULE)[0].endswith("/ae_paths/" + TST_MODULE)

        assert len(path_items("{cwd}/**/*" + '.py')) == 4  # ...setup.py, ...paths.py, ...test_paths.py, ...conftest.py
        assert all(_.endswith('.py') for _ in path_items("{cwd}/**/*" + '.py'))
        assert all(_.startswith("/") for _ in path_items("{cwd}/**/*" + '.py'))

    def test_wildcards(self):
        assert path_items("*" + '.py') == [TST_SETUP]
        assert path_items("**" + '.py') == [TST_SETUP]

        assert path_items("set??" + '.py') == [TST_SETUP]
        assert path_items("setup*" + '.py') == [TST_SETUP]
        assert path_items("setup**" + '.py') == [TST_SETUP]

        assert TST_MODULE in path_items("ae/**")
        assert path_items("ae/**/*" + '.py') == [TST_MODULE]
        assert path_items("**/pat?s" + '.py') == [TST_MODULE]

        assert len(path_items("**/*" + '.py')) == 4
        assert set(path_items("**/*" + '.py')) == {
            TST_SETUP, TST_MODULE, TST_TESTS_MODULE, TST_TESTS_CONF_PATH}

        assert path_items("{cwd}/**/paths" + '.py')[0].endswith("ae_paths/" + TST_MODULE)
        assert path_items("{cwd}/**/paths.?y")[0].endswith("ae_paths/" + TST_MODULE)

        assert len(path_items("{cwd}/**/*paths" + '.py')) == 2
        assert len(path_items("{cwd}/**/*paths.?y")) == 2

    def test_without_placeholders_and_wildcards(self):
        assert path_items(TST_SETUP) == [TST_SETUP]
        assert path_items(TST_MODULE) == [TST_MODULE]

        assert path_items(TST_FOLDER_TESTS) == [TST_FOLDER_TESTS]
        assert TST_TESTS_MODULE not in path_items(TST_FOLDER_TESTS)
        assert path_items(TST_TESTS_MODULE) == [TST_TESTS_MODULE]

        assert path_items(TST_TMP_ROOT) == [TST_TMP_ROOT]

        assert path_items("../ae_paths") == ["../ae_paths"]
        assert path_items("../ae_paths/" + TST_SETUP) == ["../ae_paths/" + TST_SETUP]

        assert path_items(".") == ["."]
        assert all(_[0] == "." for _ in path_items("."))
        assert path_items("./" + TST_SETUP) == ["./" + TST_SETUP]

        assert path_items('ae') == ['ae']
        assert TST_MODULE not in path_items('ae')        # can also contain __pycache__/paths.cpython-36.pyc
        assert path_items(TST_MODULE) == [TST_MODULE]


class TestPathPlaceholdersGlobal:
    def test_add_common_storage_paths(self):
        paths_count = len(PATH_PLACEHOLDERS)
        add_common_storage_paths()
        assert len(PATH_PLACEHOLDERS) >= paths_count                # 6 >= 6
        if 'CI_PROJECT_ID' not in os.environ:                       # skip on GitLab CI
            assert len(PATH_PLACEHOLDERS) > paths_count
            if plyer_is_importable:
                assert 'application' in PATH_PLACEHOLDERS
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
        assert normalize(f_path, make_absolute=False, remove_dots=False) == os_path_realpath(f_path)
        assert normalize(f_path, make_absolute=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False) == os_path_realpath(f_path)
        assert normalize(f_path, remove_dots=False, resolve_sym_links=False) == os_path_abspath(f_path)
        assert normalize(f_path, remove_dots=False) == os_path_realpath(f_path)
        assert normalize(f_path, resolve_sym_links=False) == os_path_abspath(f_path)
        assert normalize(f_path) == os_path_realpath(f_path)

        f_path = os_path_join(TST_TMP_ROOT, "norm_test.tst")
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False, remove_dots=False) == os_path_realpath(f_path)
        assert normalize(f_path, make_absolute=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False) == os_path_realpath(f_path)
        assert normalize(f_path, remove_dots=False, resolve_sym_links=False) == os_path_abspath(f_path)
        assert normalize(f_path, remove_dots=False) == os_path_realpath(f_path)
        assert normalize(f_path, resolve_sym_links=False) == os_path_abspath(f_path)
        assert normalize(f_path) == os_path_realpath(f_path)
        assert normalize(f_path, remove_base_path=TST_TMP_ROOT) == "norm_test.tst"
        assert normalize(f_path, remove_base_path=TST_TMP_ROOT) == os_path_relpath(f_path, TST_TMP_ROOT)
        assert normalize(f_path, remove_base_path='_not_existing_').startswith("../")
        assert normalize(f_path, remove_base_path='_not_existing_').endswith(".." + f_path)

        f_path = f"_not_existing_folder/norm_test.tst"
        assert normalize(f_path, make_absolute=False, remove_dots=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False, remove_dots=False) == os_path_realpath(f_path)
        assert normalize(f_path, make_absolute=False, resolve_sym_links=False) == f_path
        assert normalize(f_path, make_absolute=False) == os_path_realpath(f_path)
        assert normalize(f_path, remove_dots=False, resolve_sym_links=False) == os_path_abspath(f_path)
        assert normalize(f_path, remove_dots=False) == os_path_realpath(f_path)
        assert normalize(f_path, resolve_sym_links=False) == os_path_abspath(f_path)
        assert normalize(f_path) == os_path_realpath(f_path)
        assert normalize(f_path, remove_base_path=TST_TMP_ROOT).endswith(f_path)
        assert normalize(f_path, remove_base_path=TST_TMP_ROOT) == os_path_relpath(f_path, TST_TMP_ROOT)
        assert normalize(f_path, remove_base_path='_not_existing_') == os_path_join("..", f_path)
        assert normalize(f_path, remove_base_path=TST_TMP_ROOT).endswith(f_path)

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
        file_path = os_path_join(os.getcwd(), f_name)
        assert placeholder_key(f_name) == ""
        assert placeholder_key(file_path) == "cwd"
        assert placeholder_key(file_path).format(**PATH_PLACEHOLDERS) == "cwd"
        assert format_given(placeholder_key(file_path), PATH_PLACEHOLDERS) == "cwd"

    def test_placeholder_path(self):
        f_name = "test.tst"
        file_path = os_path_join(os.getcwd(), f_name)
        assert placeholder_path(f_name) == f_name
        assert placeholder_path(file_path) == "{cwd}" + "/" + f_name
        assert placeholder_path(file_path).format(**PATH_PLACEHOLDERS) == file_path
        assert format_given(placeholder_path(file_path), PATH_PLACEHOLDERS) == file_path
        assert normalize(placeholder_path(file_path)) == file_path

    def test_placeholder_path_exact_dir_name(self):
        f_name = "test.tst"
        file_path = os_path_join(os.getcwd() + "_dir_name_extended", f_name)
        assert not placeholder_path(file_path).startswith("{cwd}")
        # the next assertion would fail because placeholder_path(file_path) == "{home}/src/ae_paths_extended/test.tst"
        # assert placeholder_path(file_path) == file_path


class TestProjectPaths:
    def test_cwd_path(self):
        assert 'cwd' in PATH_PLACEHOLDERS
        assert PATH_PLACEHOLDERS['cwd'] == os.getcwd()


class TestSeriesFileName:
    def test_series_file_name_basics(self, tmp_path):
        file_mask = os_path_join(str(tmp_path), "series_tests*.tst")
        file_path = file_mask.replace("*", "")

        assert series_file_name(file_path) == file_mask.replace("*", " 01")
        assert not os_path_isfile(file_mask.replace("*", " 01"))

        assert series_file_name(file_path, marker='_copy_') == file_mask.replace("*", '_copy_' + "01")
        assert not os_path_isfile(file_mask.replace("*", '_copy_' + "01"))

        assert series_file_name(file_path, digits=1) == file_mask.replace("*", " 1")
        assert not os_path_isfile(file_mask.replace("*", " 1"))

        assert series_file_name(file_path, create=True, digits=1, marker='_') == file_mask.replace("*", "_1")
        assert not os_path_isfile(file_mask.replace("*", " 1"))

    def test_series_file_name_conflict_in_create(self, tmp_path):
        file_mask = os_path_join(str(tmp_path), "series_tests*.tst")
        file_path = file_mask.replace("*", "")

        write_file(file_mask.replace("*", " aaa"), "any content")
        write_file(file_mask.replace("*", " 04"), "any")

        assert series_file_name(file_path, create=True) == file_mask.replace("*", " 03")
        assert os_path_isfile(file_mask.replace("*", " 03"))

        assert series_file_name(file_path, create=True) == file_mask.replace("*", " 05")
        assert os_path_isfile(file_mask.replace("*", " 05"))

    def test_series_file_name_create(self, tmp_path):
        file_mask = os_path_join(str(tmp_path), "series_tests*.tst")
        file_path = file_mask.replace("*", "")

        assert series_file_name(file_path, create=True) == file_mask.replace("*", " 01")
        assert os_path_isfile(file_mask.replace("*", " 01"))

        assert series_file_name(file_path, create=True) == file_mask.replace("*", " 02")
        assert os_path_isfile(file_mask.replace("*", " 02"))


class TestUserDataPath:
    @pytest.mark.parametrize("platform", ('linux', 'freebsd', 'any_other_os'))
    def test_user_data_path_all_linux(self, platform):
        tst_dir = "/.config"

        with patch('ae.paths.os_platform', platform):
            assert user_data_path().endswith(tst_dir)

        with patch('ae.paths.os_platform', platform), patch.dict('os.environ', dict(XDG_CONFIG_HOME="")):
            assert user_data_path().endswith(tst_dir)

        with patch('ae.paths.os_platform', platform), patch.dict('os.environ', dict(XDG_CONFIG_HOME=tst_dir)):
            assert user_data_path().endswith(tst_dir)

    def test_user_data_path_android(self):
        mock_jnius = MagicMock()
        mock_cls = mock_jnius.cast.return_value
        mock_cls.getAbsolutePath.return_value = '/android/tst/data/dir'

        with (patch('ae.paths.os_platform', 'android'),
              patch('ae.paths.importlib.import_module', return_value=mock_jnius) as imp_mock):
            assert user_data_path() == '/android/tst/data/dir'

        imp_mock.assert_called_once_with('jnius')
        mock_jnius.autoclass.assert_called_once_with('org.kivy.android.PythonActivity')

    def test_user_data_path_cygwin(self):
        test_root = "/test_path"
        with patch('ae.paths.os_platform', 'cygwin'), patch.dict('os.environ', dict(APPDATA=test_root)):
            assert user_data_path() == test_root

    def test_user_data_path_darwin(self):
        with patch('ae.paths.os_platform', 'darwin'):
            assert user_data_path() == os_path_expanduser(os_path_join("~", "Library", "Application Support"))

    def test_user_data_path_ios(self):
        with patch('ae.paths.os_platform', 'ios'):
            assert user_data_path() == os_path_expanduser(os_path_join("~", "Documents"))

    def test_user_data_path_placeholder(self):
        assert 'usr' in PATH_PLACEHOLDERS

    # @pytest.mark.skipif("os_platform != 'android'", reason="android-only test")
    # def test_user_data_path_running_android(self):
    #     with patch.dict('os.environ', dict(ANDROID_ARGUMENT='any_value')):
    #         assert user_data_path()
    #     with patch.dict('os.environ', dict(KIVY_BUILD='any_value')):
    #         assert user_data_path()

    def test_user_data_path_win32(self):
        test_root = "/test_path"
        with patch('ae.paths.os_platform', 'win32'), patch.dict('os.environ', dict(APPDATA=test_root)):
            assert user_data_path() == test_root


class TestUserDocsPath:
    @pytest.mark.parametrize("platform", ('darwin', 'ios', 'linux', 'freebsd', 'any_other_os'))
    def test_user_docs_path_all_posix(self, platform):
        with patch('ae.paths.os_platform', platform):
            assert user_docs_path() == os_path_expanduser(os_path_join("~", "Documents"))

    def test_user_docs_path_android(self):
        mock_jnius = MagicMock()
        mock_cls = mock_jnius.autoclass.return_value
        mock_cls.DIRECTORY_DOCUMENTS = 'DocumentsDir'
        mock_cls.getExternalStoragePublicDirectory.return_value.getAbsolutePath.return_value = '/android/tst/docs/dir'

        with (patch('ae.paths.os_platform', 'android'),
              patch('ae.paths.importlib.import_module', return_value=mock_jnius) as imp_mock):
            assert user_docs_path() == '/android/tst/docs/dir'

        imp_mock.assert_called_once_with('jnius')
        mock_jnius.autoclass.assert_called_once_with('android.os.Environment')
        mock_cls.getExternalStoragePublicDirectory.assert_called_once_with('DocumentsDir')

    def test_user_docs_path_cygwin(self):
        test_root = "/tst_usr_root"
        with patch('ae.paths.os_platform', 'cygwin'), patch.dict('os.environ', dict(USERPROFILE=test_root)):
            assert user_docs_path() == test_root + "/Documents"

    def test_user_docs_path_darwin(self):
        with patch('ae.paths.os_platform', 'darwin'):
            assert user_docs_path() == os_path_expanduser(os_path_join("~", "Documents"))

    def test_user_docs_path_ios(self):
        with patch('ae.paths.os_platform', 'ios'):
            assert user_docs_path() == os_path_expanduser(os_path_join("~", "Documents"))

    def test_user_docs_path_placeholder(self):
        assert 'doc' in PATH_PLACEHOLDERS

    # @pytest.mark.skipif("os_platform != 'android'", reason="android-only test")
    # def test_user_docs_path_running_on_android(self):
    #     with patch.dict('os.environ', dict(ANDROID_ARGUMENT='any_value')):
    #         assert user_docs_path()
    #     with patch.dict('os.environ', dict(KIVY_BUILD='any_value')):
    #         assert user_docs_path()

    def test_user_docs_path_win32(self):
        test_root = "/test_usr_path"
        with patch('ae.paths.os_platform', 'win32'), patch.dict('os.environ', dict(USERPROFILE=test_root)):
            assert user_docs_path() == test_root + "/Documents"
