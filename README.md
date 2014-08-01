manga-downloader
=================

A python script to download manga chapters from various collection sites
e.g. Batoto.net.

You need the following python packages installed in your environment
(presumably through pip):
1. lxml

You run the script like this:
python manga-downloader.py

\[python exe path, systemic or virtual environment\] \[script path\]

This then asks for the URL. Simply put in the URL to the main
page *for the manga*, in a supported site (e.g. Batoto.net).

Example input: http://www.batoto.net/comic/_/all-you-need-is-kill-r10854

The script then starts running and creates a folder in your working
directory named like: "Batoto
\- \[manga name\]". The folder name prefix denotes the site where the
manga is downloaded from. The chapters are created as compressed ZIP archives
within this folder.

*Currently Supported Sites:*

1. Batoto
2. Starkana

*Wishlist:*
- Volume-based archiving when volume is known
- ZIP/RAR/CBZ/CBR options
- Batoto search function based on manga name
- Other sites?
- Downloading from last chapter
- Chapter min/max bounds for downloading
