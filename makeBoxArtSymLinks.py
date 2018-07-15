
import re
import os
import glob

root = '/home/pi'

for img in glob.glob(root + '/RetroPie/roms/*/downloaded_images_large/*'):

    emulatorName = re.match('.*roms\/(.*)\/downloaded_images_large\/', img)
    if not emulatorName:
        print 'bad regex'
        continue
    emulatorName = emulatorName.group(1)

    targetimgdir = root + '/.emulationstation/downloaded_images/' + emulatorName

    if not os.path.exists(targetimgdir):
        print 'mkdir', targetimgdir
        os.makedirs(targetimgdir)

    fp, fn = os.path.split(img)

    targetLinkName = os.path.join(targetimgdir, fn)

    if os.path.islink(targetLinkName):
        continue

    print 'ln -s', fn
    os.symlink(img, targetLinkName)

