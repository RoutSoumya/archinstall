from pathlib import Path

from archinstall import Installer, ProfileConfiguration, profile_handler
from archinstall.default_profiles.minimal import MinimalProfile
from archinstall import disk
from archinstall.lib.models import User

# we're creating a new ext4 filesystem installation
fs_type = disk.FilesystemType('ext4')
device_path = Path('/dev/sda')

# get the physical disk device
device = disk.device_handler.get_device(device_path)

if not device:
	raise ValueError('No device found for given path')

# create a new modification for the specific device
device_modification = disk.DeviceModification(device, wipe=True)

# create a new boot partition
boot_partition = disk.PartitionModification(
	status=disk.ModificationStatus.Create,
	type=disk.PartitionType.Primary,
	start=disk.Size(1, disk.Unit.MiB),
	length=disk.Size(512, disk.Unit.MiB),
	mountpoint=Path('/boot'),
	fs_type=disk.FilesystemType.Fat32,
	flags=[disk.PartitionFlag.Boot]
)
device_modification.add_partition(boot_partition)

# create a root partition
root_partition = disk.PartitionModification(
	status=disk.ModificationStatus.Create,
	type=disk.PartitionType.Primary,
	start=disk.Size(513, disk.Unit.MiB),
	length=disk.Size(20, disk.Unit.GiB),
	mountpoint=None,
	fs_type=fs_type,
	mount_options=[],
)
device_modification.add_partition(root_partition)

# create a new home partition
home_partition = disk.PartitionModification(
	status=disk.ModificationStatus.Create,
	type=disk.PartitionType.Primary,
	start=root_partition.length,
	length=disk.Size(100, disk.Unit.Percent, total_size=device.device_info.total_size),
	mountpoint=Path('/home'),
	fs_type=fs_type,
	mount_options=[]
)
device_modification.add_partition(home_partition)

disk_config = disk.DiskLayoutConfiguration(
	config_type=disk.DiskLayoutType.Default,
	device_modifications=[device_modification]
)

# disk encryption configuration (Optional)
disk_encryption = disk.DiskEncryption(
	encryption_password="enc_password",
	encryption_type=disk.EncryptionType.Partition,
	partitions=[home_partition],
	hsm_device=None
)

# initiate file handler with the disk config and the optional disk encryption config
fs_handler = disk.FilesystemHandler(disk_config, disk_encryption)

# perform all file operations
# WARNING: this will potentially format the filesystem and delete all data
fs_handler.perform_filesystem_operations(show_countdown=False)

mountpoint = Path('/tmp')

with Installer(
	mountpoint,
	disk_config,
	disk_encryption=disk_encryption,
	kernels=['linux']
) as installation:
	installation.mount_ordered_layout()
	installation.minimal_installation(hostname='minimal-arch')
	installation.add_additional_packages(['nano', 'wget', 'git'])

# Optionally, install a profile of choice.
# In this case, we install a minimal profile that is empty
profile_config = ProfileConfiguration(MinimalProfile())
profile_handler.install_profile_config(installation, profile_config)

user = User('archinstall', 'password', True)
installation.create_users(user)
