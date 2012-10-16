if [ $# -ne 1 ]; then
	echo Usage: "$0" '{YOUTUBEURL}'
	exit 1
fi
mkdir -p output
mkdir -p orig
youtube-dl -o video "$1" && ffmpeg -i video -r 1 -qscale 2 "orig/img%05d.jpg"
if [ $? -eq 0 ]; then
	for i in orig/*.jpg; do
		convert $i -resize 320x -gravity center -crop 320x240+0+0 +repage "output/$(basename $i)"
		echo converted $i
		mogrify -strip $i
		echo stripped $i
	done
	rm -rf orig video
else
	rm -rf orig output
fi

