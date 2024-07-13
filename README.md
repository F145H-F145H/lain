本程序是 F145H (cn同F145H) 基于qq机器人开发的漫展查询qqbot，目前支持功能：根据地名查询近期漫展（数据来自bilibili会员购）正在不断完善和优化中。

项目名来源于动漫铃音的lain，
同时也是糖糖（ame、雨）的rain同音。

_____
## 准备工作

### 安装
```bash
pip install qq-botpy python-Levenshtein
```

```bash
git clone https://github.com/F145H-F145H/lain.git
```

要在`config.yaml`文件中输入在`q.qq.com`获取的官方机器人的`appid`和`secret`
```bash
python3 robot.py
```

在QQ中艾特 使用 `@qqbot /会展 地名`进行查询
