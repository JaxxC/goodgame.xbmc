rm plugin.video.goodgame.zip
find . -name "*.pyc" -exec rm -rf {} \;
zip -9 -r plugin.video.goodgame.zip plugin.video.goodgame
cp plugin.video.goodgame.zip plugin.video.goodgame-2.0.0.zip