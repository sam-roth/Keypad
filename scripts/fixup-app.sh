#!/bin/sh

# Here's the deal: Jedi can't handle zipimports, but py2app expects a zipped
# stdlib. We compromise by unzipping the stdlib into a **directory** called
# python33.zip. (That's not a typo, that's a directory named python33.zip.)

cd ..
cd ./dist/KeyPad.app/Contents/Resources/lib

mv python33.zip python33-data.zip
mkdir python33.zip 
cd python33.zip
unzip ../python33-data.zip
cd ..
rm python33-data.zip

cd ../../Frameworks

for lib in ../Resources/lib/python33.zip/PyQt4/*.so*; do
    install_name_tool -change QtCore.framework/Versions/4/QtCore @executable_path/../Frameworks/QtCore.framework/Versions/4/QtCore $lib
    install_name_tool -change QtGui.framework/Versions/4/QtGui @executable_path/../Frameworks/QtGui.framework/Versions/4/QtGui $lib
done

cd ../../.. # dist


# This gives a warning about not finding any paths that need to be changed, 
# but it doesn't apply to what we're doing. We're just copying plugins into
# the bundle.
macdeployqt KeyPad.app


