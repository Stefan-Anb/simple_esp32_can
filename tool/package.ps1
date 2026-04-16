# get git description
$desc = git describe --tags --always

# create USB update package
mkdir package
mkdir package/bootloader
mkdir package/partition_table

cp ../build/simple_esp32_can.bin package/
cp ../build/bootloader/bootloader.bin package/bootloader/
cp ../build/partition_table/partition-table.bin package/partition_table/
cp ../build/ota_data_initial.bin package/
cp ./usb_manifest.json package/manifest.json


Compress-Archive -Path .\package\* -DestinationPath "package-usbupdate-$desc.zip" -Force

rm -r package