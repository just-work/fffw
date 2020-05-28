from unittest import TestCase

from pymediainfo import MediaInfo  # type: ignore

from fffw.graph import meta

SAMPLE = '''<?xml version="1.0" encoding="UTF-8"?>
<Mediainfo version="19.09">
<File>
<track type="General">
<Count>331</Count>
<Count_of_stream_of_this_kind>1</Count_of_stream_of_this_kind>
<Kind_of_stream>General</Kind_of_stream>
<Kind_of_stream>General</Kind_of_stream>
<Stream_identifier>0</Stream_identifier>
<Count_of_video_streams>1</Count_of_video_streams>
<Count_of_audio_streams>1</Count_of_audio_streams>
<Video_Format_List>AVC</Video_Format_List>
<Video_Format_WithHint_List>AVC</Video_Format_WithHint_List>
<Codecs_Video>AVC</Codecs_Video>
<Audio_Format_List>AAC LC</Audio_Format_List>
<Audio_Format_WithHint_List>AAC LC</Audio_Format_WithHint_List>
<Audio_codecs>AAC LC</Audio_codecs>
<Complete_name>/home/tumbler/Dropbox/Video/test_hd.mp4</Complete_name>
<Folder_name>/home/tumbler/Dropbox/Video</Folder_name>
<File_name_extension>test_hd.mp4</File_name_extension>
<File_name>test_hd</File_name>
<File_extension>mp4</File_extension>
<Format>MPEG-4</Format>
<Format>MPEG-4</Format>
<Format_Extensions_usually_used>braw mov mp4 m4v m4a m4b m4p m4r 3ga 3gpa 3gpp 3gp 3gpp2 3g2 k3g jpm jpx mqv ismv isma ismt f4a f4b f4v</Format_Extensions_usually_used>
<Commercial_name>MPEG-4</Commercial_name>
<Format_profile>Base Media</Format_profile>
<Internet_media_type>video/mp4</Internet_media_type>
<Codec_ID>isom</Codec_ID>
<Codec_ID>isom (isom/iso2/avc1/mp41)</Codec_ID>
<Codec_ID_Url>http://www.apple.com/quicktime/download/standalone.html</Codec_ID_Url>
<CodecID_Compatible>isom/iso2/avc1/mp41</CodecID_Compatible>
<File_size>3812658</File_size>
<File_size>3.64 MiB</File_size>
<File_size>4 MiB</File_size>
<File_size>3.6 MiB</File_size>
<File_size>3.64 MiB</File_size>
<File_size>3.636 MiB</File_size>
<Duration>6742</Duration>
<Duration>6 s 742 ms</Duration>
<Duration>6 s 742 ms</Duration>
<Duration>6 s 742 ms</Duration>
<Duration>00:00:06.742</Duration>
<Duration>00:00:06:37</Duration>
<Duration>00:00:06.742 (00:00:06:37)</Duration>
<Overall_bit_rate>4524068</Overall_bit_rate>
<Overall_bit_rate>4 524 kb/s</Overall_bit_rate>
<Frame_rate>50.000</Frame_rate>
<Frame_rate>50.000 FPS</Frame_rate>
<Frame_count>337</Frame_count>
<Stream_size>9605</Stream_size>
<Stream_size>9.38 KiB (0%)</Stream_size>
<Stream_size>9 KiB</Stream_size>
<Stream_size>9.4 KiB</Stream_size>
<Stream_size>9.38 KiB</Stream_size>
<Stream_size>9.380 KiB</Stream_size>
<Stream_size>9.38 KiB (0%)</Stream_size>
<Proportion_of_this_stream>0.00252</Proportion_of_this_stream>
<HeaderSize>40</HeaderSize>
<DataSize>3803061</DataSize>
<FooterSize>9557</FooterSize>
<IsStreamable>No</IsStreamable>
<File_last_modification_date>UTC 2014-11-10 11:57:35</File_last_modification_date>
<File_last_modification_date__local_>2014-11-10 14:57:35</File_last_modification_date__local_>
<Writing_application>Lavf53.32.100</Writing_application>
<Writing_application>Lavf53.32.100</Writing_application>
</track>
<track type="Video">
<Count>378</Count>
<Count_of_stream_of_this_kind>1</Count_of_stream_of_this_kind>
<Kind_of_stream>Video</Kind_of_stream>
<Kind_of_stream>Video</Kind_of_stream>
<Stream_identifier>0</Stream_identifier>
<StreamOrder>0</StreamOrder>
<ID>1</ID>
<ID>1</ID>
<Format>AVC</Format>
<Format>AVC</Format>
<Format_Info>Advanced Video Codec</Format_Info>
<Format_Url>http://developers.videolan.org/x264.html</Format_Url>
<Commercial_name>AVC</Commercial_name>
<Format_profile>High@L4.2</Format_profile>
<Format_settings>CABAC / 4 Ref Frames</Format_settings>
<Format_settings__CABAC>Yes</Format_settings__CABAC>
<Format_settings__CABAC>Yes</Format_settings__CABAC>
<Format_settings__Reference_frames>4</Format_settings__Reference_frames>
<Format_settings__Reference_frames>4 frames</Format_settings__Reference_frames>
<Internet_media_type>video/H264</Internet_media_type>
<Codec_ID>avc1</Codec_ID>
<Codec_ID_Info>Advanced Video Coding</Codec_ID_Info>
<Duration>6740</Duration>
<Duration>6 s 740 ms</Duration>
<Duration>6 s 740 ms</Duration>
<Duration>6 s 740 ms</Duration>
<Duration>00:00:06.740</Duration>
<Duration>00:00:06:37</Duration>
<Duration>00:00:06.740 (00:00:06:37)</Duration>
<Bit_rate>4321426</Bit_rate>
<Bit_rate>4 321 kb/s</Bit_rate>
<Width>1920</Width>
<Width>1 920 pixels</Width>
<Height>1080</Height>
<Height>1 080 pixels</Height>
<Stored_Height>1088</Stored_Height>
<Sampled_Width>1920</Sampled_Width>
<Sampled_Height>1080</Sampled_Height>
<Pixel_aspect_ratio>1.000</Pixel_aspect_ratio>
<Display_aspect_ratio>1.778</Display_aspect_ratio>
<Display_aspect_ratio>16:9</Display_aspect_ratio>
<Rotation>0.000</Rotation>
<Frame_rate_mode>CFR</Frame_rate_mode>
<Frame_rate_mode>Constant</Frame_rate_mode>
<FrameRate_Mode_Original>VFR</FrameRate_Mode_Original>
<Frame_rate>50.000</Frame_rate>
<Frame_rate>50.000 FPS</Frame_rate>
<Frame_count>337</Frame_count>
<Color_space>YUV</Color_space>
<Chroma_subsampling>4:2:0</Chroma_subsampling>
<Chroma_subsampling>4:2:0</Chroma_subsampling>
<Bit_depth>8</Bit_depth>
<Bit_depth>8 bits</Bit_depth>
<Scan_type>Progressive</Scan_type>
<Scan_type>Progressive</Scan_type>
<Bits__Pixel_Frame_>0.042</Bits__Pixel_Frame_>
<Stream_size>3640801</Stream_size>
<Stream_size>3.47 MiB (95%)</Stream_size>
<Stream_size>3 MiB</Stream_size>
<Stream_size>3.5 MiB</Stream_size>
<Stream_size>3.47 MiB</Stream_size>
<Stream_size>3.472 MiB</Stream_size>
<Stream_size>3.47 MiB (95%)</Stream_size>
<Proportion_of_this_stream>0.95492</Proportion_of_this_stream>
<Writing_library>x264 - core 120 r2151 a3f4407</Writing_library>
<Writing_library>x264 core 120 r2151 a3f4407</Writing_library>
<Encoded_Library_Name>x264</Encoded_Library_Name>
<Encoded_Library_Version>core 120 r2151 a3f4407</Encoded_Library_Version>
<Encoding_settings>cabac=1 / ref=3 / deblock=1:0:0 / analyse=0x3:0x113 / me=hex / subme=7 / psy=1 / psy_rd=1.00:0.00 / mixed_ref=1 / me_range=16 / chroma_me=1 / trellis=1 / 8x8dct=1 / cqm=0 / deadzone=21,11 / fast_pskip=1 / chroma_qp_offset=-2 / threads=3 / sliced_threads=0 / nr=0 / decimate=1 / interlaced=0 / bluray_compat=0 / constrained_intra=0 / bframes=3 / b_pyramid=2 / b_adapt=1 / b_bias=0 / direct=1 / weightb=1 / open_gop=0 / weightp=2 / keyint=250 / keyint_min=25 / scenecut=40 / intra_refresh=0 / rc_lookahead=40 / rc=crf / mbtree=1 / crf=23.0 / qcomp=0.60 / qpmin=0 / qpmax=69 / qpstep=4 / ip_ratio=1.40 / aq=1:1.00</Encoding_settings>
<Codec_configuration_box>avcC</Codec_configuration_box>
</track>
<track type="Audio">
<Count>280</Count>
<Count_of_stream_of_this_kind>1</Count_of_stream_of_this_kind>
<Kind_of_stream>Audio</Kind_of_stream>
<Kind_of_stream>Audio</Kind_of_stream>
<Stream_identifier>0</Stream_identifier>
<StreamOrder>1</StreamOrder>
<ID>2</ID>
<ID>2</ID>
<Format>AAC</Format>
<Format>AAC LC</Format>
<Format_Info>Advanced Audio Codec Low Complexity</Format_Info>
<Commercial_name>AAC</Commercial_name>
<Format_AdditionalFeatures>LC</Format_AdditionalFeatures>
<Codec_ID>mp4a-40-2</Codec_ID>
<Duration>6742</Duration>
<Duration>6 s 742 ms</Duration>
<Duration>6 s 742 ms</Duration>
<Duration>6 s 742 ms</Duration>
<Duration>00:00:06.742</Duration>
<Duration>00:00:06:34</Duration>
<Duration>00:00:06.742 (00:00:06:34)</Duration>
<Bit_rate_mode>CBR</Bit_rate_mode>
<Bit_rate_mode>Constant</Bit_rate_mode>
<Bit_rate>192000</Bit_rate>
<Bit_rate>192 kb/s</Bit_rate>
<Channel_s_>6</Channel_s_>
<Channel_s_>6 channels</Channel_s_>
<Channel_positions>Front: L C R, Side: L R, LFE</Channel_positions>
<Channel_positions>3/2/0.1</Channel_positions>
<Channel_layout>C L R Ls Rs LFE</Channel_layout>
<Samples_per_frame>1024</Samples_per_frame>
<Sampling_rate>48000</Sampling_rate>
<Sampling_rate>48.0 kHz</Sampling_rate>
<Samples_count>323616</Samples_count>
<Frame_rate>46.875</Frame_rate>
<Frame_rate>46.875 FPS (1024 SPF)</Frame_rate>
<Frame_count>316</Frame_count>
<Compression_mode>Lossy</Compression_mode>
<Compression_mode>Lossy</Compression_mode>
<Stream_size>162252</Stream_size>
<Stream_size>158 KiB (4%)</Stream_size>
<Stream_size>158 KiB</Stream_size>
<Stream_size>158 KiB</Stream_size>
<Stream_size>158 KiB</Stream_size>
<Stream_size>158.4 KiB</Stream_size>
<Stream_size>158 KiB (4%)</Stream_size>
<Proportion_of_this_stream>0.04256</Proportion_of_this_stream>
<Default>Yes</Default>
<Default>Yes</Default>
<Alternate_group>1</Alternate_group>
<Alternate_group>1</Alternate_group>
</track>
</File>
</Mediainfo>
'''


class MetaDataTestCase(TestCase):
    def setUp(self) -> None:
        self.media_info = MediaInfo(SAMPLE)

    def test_parse_streams(self):
        streams = meta.from_media_info(self.media_info)
        self.assertEqual(len(streams), 2)
        video = streams[0]
        self.assertIsInstance(video, meta.VideoMeta)
        expected = meta.VideoMeta(
            duration=meta.TS(6.740),
            start=meta.TS(0),
            bitrate=4321426,
            width=1920,
            height=1080,
            par=1.0,
            dar=1.778,
            frame_rate=50.0,
            frames=337,
        )
        self.assertEqual(expected, video)
        audio = streams[1]
        self.assertIsInstance(audio, meta.AudioMeta)
        expected = meta.AudioMeta(
            duration=meta.TS(6.742),
            start=meta.TS(0),
            bitrate=192000,
            sampling_rate=48000,
            channels=6,
            samples=323616,
        )
        self.assertEqual(expected, audio)
