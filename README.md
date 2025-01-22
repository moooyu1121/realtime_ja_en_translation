# realtime_translation
リアルタイム日本語 ⇔ 英語翻訳をします。

マイクから音声を拾って、英語なら日本語に、日本語なら英語に翻訳します。

マイクの音を拾う → google-speech-to-text(Google cloudのapi使用) → google翻訳のapi(こちらは無料) → streamlitで表示
という流れになっています。

https://cloud.google.com/speech-to-text?utm_source=google&utm_medium=cpc&utm_campaign=japac-JP-all-en-dr-BKWS-all-pkws-trial-PHR-dr-1605216&utm_content=text-ad-none-none-DEV_c-CRE_654190887034-ADGP_Hybrid+%7C+BKWS+-+BRO+%7C+Txt+-AI+%26+ML-Speech+to+Text-google+audio+to+text-main-KWID_43700075964501439-kwd-1879918006449&userloc_9198686-network_g&utm_term=KW_google+audio+to+text+conversion&gad_source=1&gclid=Cj0KCQiAy8K8BhCZARIsAKJ8sfR7584L4Cirtj-SNgw464hK_LKhjOPBFgPvOYDw_He-FpQIjiWBK-caAspqEALw_wcB&gclsrc=aw.ds

Google cloud の speech-to-textのapiを使います。

https://www.youtube.com/watch?v=izdDHVLc_Z0

このへんのを参考に.jsonのapiキーを作成し、main.py内のGOOGLE_APPLICATION_CREDENTIALSにパスが入るようにしてください。

自動的にいい感じに区切りながら音声を読み取って行く工程は

https://tadaoyamaoka.hatenablog.com/entry/2022/10/15/175722

を"全面的"に参考にさせていただきました。本当にありがとうございました。
