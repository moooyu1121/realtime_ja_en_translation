# realtime_translation
リアルタイム日本語 ⇔ 英語翻訳をします。

スピーカーからの出力を拾って、英語なら日本語に、日本語なら英語に翻訳します。

デフォルトスピーカーの出力を拾う → whisperで文字起こし → google翻訳のapi(フリーで使えます) → streamlitで表示
という流れになっています。

whisperを動かすためのアレコレ(CUDAとcuDNNとpytorchとffmpegと、、)が必要です。

https://happy-shibusawake.com/openai_whisper/696/ 

↑
基本こちらのサイトを参考に進めてもらって大丈夫ですが、pythonのバージョンは3.7じゃなくて3.8じゃないと多分動かないです。

セイウチ演算子なるものや、fuctoolsなるものがwhisperの中で使われていて、これらはpython3.8から対応したらしいです。

pytorchはpython3.7対応となっているstableの方を入れてもらえば、python3.8でも動きました。CUDAは11.7を入れてます。

whisperを動かす土台ができていれば、あとはanaconda等でenvironment.ymlから仮想環境を作ってもらえば行ける、、、はずです。
whisperのモデルはデフォルトではmediumを読み込むようになっています。翻訳にかける都合上、文字起こしはなるべく高い精度が欲しいのでmediumかlargeがおすすめです。
![Screenshot 2023-02-13 045713](https://user-images.githubusercontent.com/87175394/218334117-19787714-1fb9-4915-b611-1c5ec32ec8b5.png)
![Screenshot 2023-02-13 050025](https://user-images.githubusercontent.com/87175394/218334121-1acc1399-1f62-4b78-8127-adc6b390904e.png)



今回、自動的にいい感じに区切りながら音声を読み取って行く工程は

https://tadaoyamaoka.hatenablog.com/entry/2022/10/15/175722

を"全面的"に参考にさせていただきました。本当にありがとうございました。

104行目、record関数内のsc.default_speakerをsc.default_microphoneに変えると、マイクから音を拾って翻訳してくれるようにもできます！
