#!/bin/sh

# - simple support to add kernel args

cwd=`pwd`
boot_iso="boot.iso"
custom_iso="custom.iso"
boot_iso_dir="/mnt/boot_iso_dir"
custom_iso_dir="/mnt/new"
kscfg=$1
guestos=$2


echo "- clean out any stale custom iso"
echo "- create work directories"
mkdir -p $boot_iso_dir
mkdir -p $custom_iso_dir

echo "- mount $boot_iso"
mount -t iso9660 -o loop $boot_iso $boot_iso_dir

echo "- copy original iso files to custom work directory"
cp -rf ${boot_iso_dir}/* $custom_iso_dir
chmod -R 777 ${custom_iso_dir}/*
umount $boot_iso_dir

vlmid=`isoinfo -d -i $boot_iso |grep 'Volume id:'`
vlmid=${vlmid#"Volume id: "}
if [ -n "`echo $vlmid|grep ppc`" ];then
       echo "- edit yaboot.conf and add kickstart entry"
       WORKING_ISO="${custom_iso_dir}/etc/yaboot.conf"
       # change timeout and  add kickstart entry
       TIMEOUT_LINE=`cat $WORKING_ISO | grep timeout | head -1`
       APPEND_LINE=`cat $WORKING_ISO | grep append | head -1`
       cat $WORKING_ISO | sed "s#${TIMEOUT_LINE}#timeout=5#" | sed "s#${APPEND_LINE}#append= \"root=live:CDLABEL=$vlmid ks=cdrom:/$kscfg \"#">  isocfgtmp
       mv -f isocfgtmp $WORKING_ISO
       cd $custom_iso_dir
       mkisofs -R -V "$vlmid" -sysid PPC -chrp-boot -U -prep-boot ppc/chrp/yaboot -hfs-bless ppc/mac -no-desktop -allow-multidot -volset 4 -volset-size 1 -volset-seqno 1 -hfs-volid 4 -o $cwd/$custom_iso .
else
       echo "- copy kickstart to custom work directory"
       cp $kscfg $custom_iso_dir

       echo "- edit isolinux.cfg and add kickstart entry"
       WORKING_ISO="${custom_iso_dir}/isolinux/isolinux.cfg"

       #use different isolinux.cfg for rhel7 ,rhel6 and rhel5 guest
       if [[ "$guestos" =~ "rhel7" ]]; then
		echo "label custom_ks
                       kernel vmlinuz $kernel_args
                       append initrd=initrd.img ks=cdrom:sr0:/$kscfg repo=cdrom:sr0 ramdisk_size=20000">>  $WORKING_ISO

       else
		echo "label custom_ks
                       kernel vmlinuz $kernel_args
                       append initrd=initrd.img ks=cdrom:/$kscfg ramdisk_size=20000 " >> $WORKING_ISO
       fi


       # change default boot target and timeout
       DEFAULT_LINE=`cat $WORKING_ISO | grep default | head -1`
       TIMEOUT_LINE=`cat $WORKING_ISO | grep timeout | head -1`

       cat $WORKING_ISO | sed "s/${DEFAULT_LINE}/default custom_ks/" | sed "s/${TIMEOUT_LINE}/timeout 5/">  isocfgtmp

       mv -f isocfgtmp $WORKING_ISO

       # cd to custom_iso_dir, otherwise mkisofs seems to bomb...
       cd $custom_iso_dir
       mkisofs -R -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -o $cwd/$custom_iso .
fi
EXITVAL=$?
if [ $EXITVAL -ne '0' ] ; then
    echo -e "\n mkisofs exited with $EXITVAL!"
fi

# clean up
rm -rf $boot_iso_dir
rm -rf $custom_iso_dir

exit
