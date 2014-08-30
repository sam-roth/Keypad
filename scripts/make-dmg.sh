#!/bin/sh

pushd ..
    hdiutil create KeyPad.dmg -srcfolder ./dist -volname KeyPad -fs HFS+ -format UDBZ
popd
