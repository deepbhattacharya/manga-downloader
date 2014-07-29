batoto-downloader-python
========================

A python script to download manga chapters from Batoto.net.

You need the following python packages installed in your environment
(presumably through pip):

1. lxml

You run the script like this:
python batoto-downloader-python.py
\[python exe path, systemic or virtual environment\] \[script path\]

This then asks for the Batoto URL. Simply put in the URL to the main
page *for the manga*.

Example input: http://www.batoto.net/comic/\_/all-you-need-is-kill-r10854

The script then starts running and creates a folder in your working
directory named like: "Batoto
\- \[manga name\]". The chapters are created as compressed ZIP archives
within this folder.

*Wishlist:*
- Volume-based archiving when volume is known
- ZIP/RAR/CBZ/CBR options
- Batoto search function based on manga name
- Other sites?
