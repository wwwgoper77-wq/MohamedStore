cat << 'EOF' > /etc/enigma2/IPAudioPro.json
{
    "Playlist": {
        "streams": [
            {
                "name": "FoX FM 1",
                "display_name": "FoX FM 1",
                "url": "http://foxfm.xyz/1#"
            },
            {
                "name": "FoX FM 2",
                "display_name": "FoX FM 2",
                "url": "http://foxfm.xyz/2#"
            },
            {
                "name": "FoX FM 3",
                "display_name": "FoX FM 3",
                "url": "http://foxfm.xyz/3#"
            },
            {
                "name": "FoX FM 4",
                "display_name": "FoX FM 4",
                "url": "http://foxfm.xyz/4#"
            },
            {
                "name": "FoX FM 5",
                "display_name": "FoX FM 5",
                "url": "http://foxfm.xyz/5#"
            },
            {
                "name": "FoX FM 6",
                "display_name": "FoX FM 6",
                "url": "http://foxfm.xyz/6#"
            },
            {
                "name": "FoX FM 7",
                "display_name": "FoX FM 7",
                "url": "http://foxfm.xyz/7#"
            },
            {
                "name": "FoX FM 8",
                "display_name": "FoX FM 8",
                "url": "http://foxfm.xyz/8#"
            },
            {
                "name": "FoX FM 9",
                "display_name": "FoX FM 9",
                "url": "http://foxfm.xyz/9#"
            },
            {
                "name": "Anis1",
                "display_name": "Anis1",
                "url": "https://anisfm.pp.ua/1"
            },
            {
                "name": "Anis1Low",
                "display_name": "Anis1Low",
                "url": "https://anisfm.pp.ua/1L"
            },
            {
                "name": "Anis2",
                "display_name": "Anis2",
                "url": "https://anisfm.pp.ua/2"
            },
            {
                "name": "Anis2Low",
                "display_name": "Anis2Low",
                "url": "https://anisfm.pp.ua/2L"
            },
            {
                "name": "Anis3",
                "display_name": "Anis3",
                "url": "https://anisfm.pp.ua/3"
            },
            {
                "name": "Anis3Low",
                "display_name": "Anis3Low",
                "url": "https://anisfm.pp.ua/3L"
            },
            {
                "name": "Anis4",
                "display_name": "Anis4",
                "url": "https://anisfm.pp.ua/4"
            },
            {
                "name": "Anis4Low",
                "display_name": "Anis4Low",
                "url": "https://anisfm.pp.ua/4L"
            },
            {
                "name": "Anis5",
                "display_name": "Anis5",
                "url": "https://anisfm.pp.ua/5"
            },
            {
                "name": "Anis5Low",
                "display_name": "Anis5Low",
                "url": "https://anisfm.pp.ua/5L"
            },
            {
                "name": "Anis FM Max 1",
                "display_name": "Anis FM Max 1",
                "url": "https://anisfm.pp.ua/Mx1"
            }
        ]
    }
}
EOF
chmod 755 /etc/enigma2/IPAudioPro.json
killall -9 enigma2