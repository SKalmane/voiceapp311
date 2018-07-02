"""
Tools to package and deploy the lambda function for the mycity voice app.
"""

from __future__ import print_function
from subprocess import run
import argparse
import os
import shutil
import zipfile
import stat
import errno

# path constants
PROJECT_ROOT = os.path.join(os.getcwd(), os.pardir, os.pardir)
TEMP_DIR_PATH = os.path.join(PROJECT_ROOT, 'temp')
LAMBDA_REL_PATH = 'platforms/amazon/lambda/custom/lambda_function.py'
LAMBDA_FUNCTION_PATH = os.path.join(PROJECT_ROOT, LAMBDA_REL_PATH)
MYCITY_PATH = os.path.join(PROJECT_ROOT, 'mycity')

ZIP_FILE_NAME = "lambda_function.zip"


def zip_lambda_function_directory(zip_target_dir):
    """
    Generates a .zip file containing the contents of the temporary directory
    where the project files have been copied. Note that this .zip file
    must contain the files with no intermediate directory.

    :param zip_target_dir: destination directory for zip file being created
    :return: none
    """
    zip_file = zipfile.ZipFile(os.path.join(zip_target_dir, ZIP_FILE_NAME), 'w')
    original_directory = os.getcwd()
    os.chdir(TEMP_DIR_PATH)
    print('Compressing ', end='')
    for root, dirs, files in os.walk('.'):
        for f in files:
            zip_file.write(os.path.join(root, f))
            print('.', end='')
    print('DONE')
    zip_file.close()
    os.chdir(original_directory)


def install_pip_dependencies(requirements_path, requirements_path_no_deps):
    """
    Installs all the dependencies for the project's entry point to a
    temporary directory the .zip file is later created from.

    :param requirements_path: path to textfile containing required libraries
    :param requirements_path_no_deps: path to textfile containing required
        libraries (whose dependencies won't be downloaded)
    :return: none
    """
    install_args = [
        "pip",
        "install",
        "-r",
        requirements_path,
        "-t",
        TEMP_DIR_PATH
    ]

    install_args_no_deps = [
        "pip",
        "install",
        "--no-deps",
        "-r",
        requirements_path_no_deps,
        "-t",
        TEMP_DIR_PATH
    ]

    print('Installing dependencies ... ', end='')
    run(install_args)
    print('Installing dependencies from requirements_no_deps.txt ...', end='')
    run(install_args_no_deps)
    print('DONE')


def package_lambda_function():
    """
    Creates a temporary directory where the lambda file and all of its
    dependencies are copied before being compressed. Removes the temporary
    directory after creating the .zip file.

    :return: none
    """
    print('Creating temporary build directory ... ', end='')
    # remove/create the temporary directory for the zip file's contents
    if os.path.exists(TEMP_DIR_PATH):
        shutil.rmtree(
            TEMP_DIR_PATH,
            ignore_errors=False,
            onerror=handle_remove_readonly
        )
    os.mkdir(TEMP_DIR_PATH)

    # copy lambda file and mycity directory to temp directory
    shutil.copy(LAMBDA_FUNCTION_PATH, TEMP_DIR_PATH)
    shutil.copytree(MYCITY_PATH, os.path.join(TEMP_DIR_PATH, 'mycity'))

    print('DONE')

    # install dependencies
    install_pip_dependencies(
        os.path.join(os.getcwd(), 'requirements.txt'),
        os.path.join(os.getcwd(), 'requirements_no_deps.txt')
    )

    # build zip file in project root
    zip_lambda_function_directory(PROJECT_ROOT)

    # delete temp directory
    print('Cleaning up ... ', end='')
    shutil.rmtree(
        TEMP_DIR_PATH,
        ignore_errors=False,
        onerror=handle_remove_readonly
    )
    print('DONE')


def handle_remove_readonly(func, path, execinfo):
    """
    Passed as the onerror parameter when calling shutil.rmtree.
    See:
    https://stackoverflow.com/a/1214935/2554154
    Handles the case where rmtree fails in Windows due to access problems.

    :param func:
    :param path:
    :param execinfo:
    :return: none
    """
    excvalue = execinfo[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        # if we're failing to remove files because they are readonly,
        # update permissions
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise Exception("Failed to delete temp folder.")


def main():
    """
    Defines the command-line option required to initiate building the zipfile.
    Conditionally begins the build process if the required option is present.

    :return: none
    """
    parser = argparse.ArgumentParser(
        description="Tools to package and deploy the lambda function for the " +
                    "MyCity app."
    )

    parser.add_argument(
        '-p',
        '--package',
        help="Creates a zip file that can be uploaded as an Amazon lambda " +
             "function",
        action='store_true'
    )

    args = parser.parse_args()

    if args.package:
        package_lambda_function()
    else:
        print("No known option selected")


if __name__ == "__main__":
    main()
