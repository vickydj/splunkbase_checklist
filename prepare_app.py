#!/usr/bin/env python3

#usage prepare_app.py <app_name>

import os
import stat
import shutil
import logging
import tarfile
import configparser
from pathlib import Path

class SplunkAppPrep:
    def __init__(self, app_path):
        self.app_path = Path(app_path)
        self.logger = self._setup_logger()
        
        # Define permission modes for Splunk Cloud requirements
        self.dir_perms = 0o755  # rwxr-xr-x
        self.file_perms = 0o644  # rw-r--r--
        self.exec_perms = 0o755  # rwxr-xr-x

        # Files that need executable permissions
        self.exec_files = {'.py', '.sh'}
        
    def _setup_logger(self):
        logger = logging.getLogger('SplunkAppPrep')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def fix_app_conf(self):
        """Remove install_source_checksum from app.conf"""
        try:
            app_conf_path = self.app_path / 'default' / 'app.conf'
            if app_conf_path.exists():
                config = configparser.ConfigParser()
                config.read(app_conf_path)
                
                # Remove install_source_checksum if it exists
                if 'install' in config and 'install_source_checksum' in config['install']:
                    del config['install']['install_source_checksum']
                    self.logger.info("Removed install_source_checksum from app.conf")
                
                # Write back the modified config
                with open(app_conf_path, 'w') as f:
                    config.write(f)
                
                # Set correct permissions
                os.chmod(app_conf_path, self.file_perms)
                
        except Exception as e:
            self.logger.error(f"Error fixing app.conf: {str(e)}")

    def fix_meta_files(self):
        """Fix metadata files according to Splunk Cloud requirements"""
        try:
            # Remove local.meta if it exists
            local_meta = self.app_path / 'metadata' / 'local.meta'
            if local_meta.exists():
                local_meta.unlink()
                self.logger.info("Removed local.meta file")

            # Create/update default.meta with proper access controls
            default_meta = self.app_path / 'metadata' / 'default.meta'
            default_meta_content = """[]
access = read : [ * ], write : [ admin ]
export = system
"""
            # Create metadata directory if it doesn't exist
            default_meta.parent.mkdir(parents=True, exist_ok=True)

            # Write default.meta with proper content and permissions
            with open(default_meta, 'w') as f:
                f.write(default_meta_content)
            
            os.chmod(default_meta, self.file_perms)
            self.logger.info("Created/Updated default.meta with proper permissions and content")

        except Exception as e:
            self.logger.error(f"Error fixing meta files: {str(e)}")

    def set_permissions(self):
        """Set Splunk Cloud compliant permissions"""
        try:
            # First set app directory permission
            os.chmod(self.app_path, self.dir_perms)
            self.logger.info(f"Set app directory permissions to 755: {self.app_path}")

            for root, dirs, files in os.walk(self.app_path):
                # Set directory permissions
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    os.chmod(dir_path, self.dir_perms)
                    self.logger.info(f"Set directory permissions to 755: {dir_path}")

                # Set file permissions
                for f in files:
                    file_path = os.path.join(root, f)
                    if Path(file_path).suffix in self.exec_files:
                        os.chmod(file_path, self.exec_perms)
                        self.logger.info(f"Set executable permissions to 755: {file_path}")
                    else:
                        os.chmod(file_path, self.file_perms)
                        self.logger.info(f"Set file permissions to 644: {file_path}")

        except Exception as e:
            self.logger.error(f"Error setting permissions: {str(e)}")

    def clean_app(self):
        """Clean unnecessary files"""
        patterns_to_remove = [
            '*.pyc',
            '__pycache__',
            '.DS_Store',
            '*.swp',
            '*~',
            '.git',
            '.gitignore',
            '*.tmp',
            '*.log'
        ]

        try:
            for pattern in patterns_to_remove:
                for path in self.app_path.rglob(pattern):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        shutil.rmtree(path)
                    self.logger.info(f"Removed: {path}")
        except Exception as e:
            self.logger.error(f"Error cleaning files: {str(e)}")

    def verify_structure(self):
        """Verify Splunk app structure"""
        required_files = ['default/app.conf']
        required_dirs = ['bin', 'default']
        
        for req_file in required_files:
            file_path = self.app_path / req_file
            if not file_path.exists():
                self.logger.warning(f"Missing required file: {req_file}")
                
        for req_dir in required_dirs:
            dir_path = self.app_path / req_dir
            if not dir_path.exists():
                self.logger.warning(f"Missing required directory: {req_dir}")

    def create_package(self):
        """Create properly structured tar.gz package"""
        try:
            # Get parent directory and app name
            parent_dir = self.app_path.parent
            app_name = self.app_path.name
            
            # Create tar.gz file
            tar_path = parent_dir / f"{app_name}.tar.gz"
            
            with tarfile.open(tar_path, "w:gz") as tar:
                # Change to parent directory to create correct structure
                os.chdir(parent_dir)
                # Add app directory with relative path
                tar.add(app_name)
            
            self.logger.info(f"Created package: {tar_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating package: {str(e)}")

    def prepare_app(self):
        """Run all preparation steps"""
        self.logger.info(f"Starting Splunk app preparation for: {self.app_path}")
        
        self.verify_structure()
        self.clean_app()
        self.fix_app_conf()  # Remove install_source_checksum
        self.fix_meta_files()  # Handle metadata files
        self.set_permissions()
        self.create_package()
        
        self.logger.info("Splunk app preparation completed")

def main():
    import sys
    if len(sys.argv) > 1:
        app_path = sys.argv[1]
    else:
        app_path = os.getcwd()

    prep = SplunkAppPrep(app_path)
    prep.prepare_app()

if __name__ == "__main__":
    main()
