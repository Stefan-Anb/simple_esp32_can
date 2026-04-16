rm -r package/
mkdir package/
cp ../build/bootloader/bootloader.bin package/
cp ../build/partition_table/partition-table.bin package/
cp ../build/ota_data_initial.bin package/
cp ../build/simple_esp32_can.bin package/