# -*- coding: utf-8 -*-


#作用是处理交互逻辑，文字输入，语音、文字及情绪的发送、播放及展示输出


import math


from operator import index


import os


import time


import socket


import requests


from pydub import AudioSegment


from queue import Queue


import re  # 添加正则表达式模块用于过滤表情符号


import uuid
import hashlib
from urllib.parse import urlparse, urljoin





# 适应模型使用


import numpy as np


from ai_module import baidu_emotion

from core.action_signal import resolve_action_signal

from core import wsa_server


from core.interact import Interact


from tts.tts_voice import EnumVoice


from scheduler.thread_manager import MyThread


from tts import tts_voice


from utils import util, config_util


from core import qa_service


from utils import config_util as cfg


from core import content_db


from ai_module import nlp_cemotion


from core import stream_manager





from core import member_db


import threading





#加载配置


cfg.load_config()


if cfg.tts_module =='ali':


    from tts.ali_tss import Speech


elif cfg.tts_module == 'gptsovits':


    from tts.gptsovits import Speech


elif cfg.tts_module == 'gptsovits_v3':


    from tts.gptsovits_v3 import Speech    


elif cfg.tts_module == 'volcano':


    from tts.volcano_tts import Speech


else:


    from tts.ms_tts_sdk import Speech





#windows运行推送唇形数据


import platform


if platform.system() == "Windows":


    import sys


    _fay_runtime_dir = os.path.abspath(os.path.dirname(__file__))
    if hasattr(sys, "_MEIPASS"):
        _fay_runtime_dir = os.path.abspath(sys._MEIPASS)
    else:
        _fay_runtime_dir = os.path.abspath(os.path.join(_fay_runtime_dir, ".."))

    _lipsync_dir = os.path.join(_fay_runtime_dir, "test", "ovr_lipsync")
    if _lipsync_dir not in map(os.path.abspath, sys.path):
        sys.path.insert(0, _lipsync_dir)


    from test_olipsync import LipSyncGenerator


    





#可以使用自动播报的标记    


can_auto_play = True


auto_play_lock = threading.RLock()





class FeiFei:


    def __init__(self):


        self.lock = threading.Lock()


        self.nlp_streams = {} # 存储用户ID到句子缓存的映射


        self.nlp_stream_lock = threading.Lock() # 保护nlp_streams字典的锁


        self.mood = 0.0  # 情绪值


        self.old_mood = 0.0


        self.item_index = 0


        self.X = np.array([1, 0, 0, 0, 0, 0, 0, 0]).reshape(1, -1)  # 适应模型变量矩阵


        # self.W = np.array([0.01577594,1.16119452,0.75828,0.207746,1.25017864,0.1044121,0.4294899,0.2770932]).reshape(-1,1) #适应模型变量矩阵


        self.W = np.array([0.0, 0.6, 0.1, 0.7, 0.3, 0.0, 0.0, 0.0]).reshape(-1, 1)  # 适应模型变量矩阵





        self.wsParam = None


        self.wss = None


        self.sp = Speech()


        self.speaking = False #声音是否在播放


        self.__running = True


        self.sp.connect()  #TODO 预连接





        self.timer = None


        self.sound_query = Queue()


        self.think_mode_users = {}  # 使用字典存储每个用户的think模式状态


        self.think_time_users = {} #使用字典存储每个用户的think开始时间
        self.think_display_state = {}
        self.think_display_limit = 400
        self.user_conv_map = {} #存储用户对话id及句子流序号，key为(username, conversation_id)

        self.pending_isfirst = {}  # 存储因prestart被过滤而延迟的isfirst标记，key为username
        self.tts_cache = {}
        self.tts_cache_limit = 1000
        self.tts_cache_lock = threading.Lock()
        self.user_audio_conv_map = {}  # 仅用于音频片段的连续序号（避免文本序号空洞导致乱序/缺包）
        self.human_audio_order_map = {}
        self.human_audio_order_lock = threading.Lock()
        self.human_audio_reorder_wait_seconds = 0.2
        self.human_audio_first_wait_seconds = 1.2

    


    def __remove_emojis(self, text):


        """


        改进的表情包过滤，避免误删除正常Unicode字符


        """


        # 更精确的emoji范围，避免误删除正常字符


        emoji_pattern = re.compile(


            "["


            "\U0001F600-\U0001F64F"  # 表情符号 (Emoticons)


            "\U0001F300-\U0001F5FF"  # 杂项符号和象形文字 (Miscellaneous Symbols and Pictographs)


            "\U0001F680-\U0001F6FF"  # 交通和地图符号 (Transport and Map Symbols)


            "\U0001F1E0-\U0001F1FF"  # 区域指示符号 (Regional Indicator Symbols)


            "\U0001F900-\U0001F9FF"  # 补充符号和象形文字 (Supplemental Symbols and Pictographs)


            "\U0001FA70-\U0001FAFF"  # 扩展A符号和象形文字 (Symbols and Pictographs Extended-A)


            "\U00002600-\U000026FF"  # 杂项符号 (Miscellaneous Symbols)


            "\U00002700-\U000027BF"  # 装饰符号 (Dingbats)


            "\U0000FE00-\U0000FE0F"  # 变体选择器 (Variation Selectors)


            "\U0001F000-\U0001F02F"  # 麻将牌 (Mahjong Tiles)


            "\U0001F0A0-\U0001F0FF"  # 扑克牌 (Playing Cards)


            "]+",


            flags=re.UNICODE,


        )





        # 保护常用的中文标点符号和特殊字符


        protected_chars = ["。", "，", "！", "？", "：", "；", "、", """, """, "'", "'", "（", "）", "【", "】", "《", "》"]





        # 先保存保护字符的位置


        protected_positions = {}


        for i, char in enumerate(text):


            if char in protected_chars:


                protected_positions[i] = char





        # 执行emoji过滤


        filtered_text = emoji_pattern.sub('', text)





        # 如果过滤后文本长度变化太大，可能误删了正常字符，返回原文本


        if len(filtered_text) < len(text) * 0.5:  # 如果删除了超过50%的内容


            return text





        return filtered_text


    def __normalize_tts_text(self, text):
        if text is None:
            return text
        text = text.replace("\u3000", " ")
        raw_lines = re.split(r"\r\n|\r|\n+", text)
        lines = []
        for line in raw_lines:
            normalized_line = re.sub(r"\s+", " ", line).strip()
            normalized_line = re.sub(r"\s+([，。！？；：、,.!?;:])", r"\1", normalized_line)
            if normalized_line:
                lines.append(normalized_line)

        if not lines:
            return ""

        merged_text = lines[0]
        for next_line in lines[1:]:
            merged_text += self.__get_tts_line_separator(merged_text, next_line)
            merged_text += next_line

        return re.sub(r"\s+", " ", merged_text).strip()


    def __get_tts_line_separator(self, previous_text, next_text):
        sentence_endings = ("。", "！", "？", "!", "?", "；", ";", "…")
        pause_endings = ("，", ",", "、", "：", ":")

        previous_text = previous_text.rstrip()
        if not previous_text:
            return ""
        if previous_text.endswith(sentence_endings) or previous_text.endswith(pause_endings):
            return ""
        if self.__contains_cjk(previous_text) or self.__contains_cjk(next_text):
            return "。"
        return ". "


    def __contains_cjk(self, text):
        return re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text or "") is not None


    def __process_stream_output(self, text, username, session_type="type2_stream", is_qa=False):


        """


        按流式方式分割和发送 type=2 的文本


        使用安全的流式文本处理器和状态管理器


        """


        if not text or text.strip() == "":


            return





        # 使用安全的流式文本处理器


        from utils.stream_text_processor import get_processor


        from utils.stream_state_manager import get_state_manager





        processor = get_processor()


        state_manager = get_state_manager()





        # 处理流式文本，is_qa=False表示普通模式


        success = processor.process_stream_text(text, username, is_qa=is_qa, session_type=session_type)





        if success:


            # 普通模式结束会话


            state_manager.end_session(username, conversation_id=stream_manager.new_instance().get_conversation_id(username))


        else:


            util.log(1, f"type=2流式处理失败，文本长度: {len(text)}")


            # 失败时也要确保结束会话


            state_manager.force_reset_user_state(username)





    #语音消息处理检查是否命中q&a


    def __get_answer(self, interleaver, text):


        answer = None


        # 全局问答


        answer, type = qa_service.QAService().question('qa',text)


        if answer is not None:


            return answer, type


        else:


            return None, None


        


       


    #消息处理


    def __process_interact(self, interact: Interact):


        if self.__running:


            try:


                index = interact.interact_type


                username = interact.data.get("user", "User")


                uid = member_db.new_instance().find_user(username)
                no_reply = interact.data.get("no_reply", False)
                if isinstance(no_reply, str):
                    no_reply = no_reply.strip().lower() in ("1", "true", "yes", "y", "on")
                else:
                    no_reply = bool(no_reply)


                


                if index == 1: #语音、文字交互


                    


                    #记录用户问题,方便obs等调用


                    self.write_to_file("./logs", "asr_result.txt",  interact.data["msg"])





                    #同步用户问题到数字人


                    if wsa_server.get_instance().is_connected(username): 


                        content = {'Topic': 'human', 'Data': {'Key': 'question', 'Value': interact.data["msg"]}, 'Username' : interact.data.get("user")}


                        wsa_server.get_instance().add_cmd(content)





                    #记录用户问题


                    if not no_reply:
                        content_id, create_ms = content_db.new_instance().add_content('member','speak',interact.data["msg"], username, uid)
                        if wsa_server.get_web_instance().is_connected(username):
                            wsa_server.get_web_instance().add_cmd({"panelReply": {"type":"member","content":interact.data["msg"], "username":username, "uid":uid, "id":content_id, "timetext": util.ms_to_timetext(create_ms)}, "Username" : username})


                    


                    observation = interact.data.get("observation", None)
                    obs_text = ""
                    if observation is not None:
                        obs_text = observation.strip() if isinstance(observation, str) else str(observation).strip()
                    if not obs_text and no_reply:
                        msg_text = interact.data.get("msg", "")
                        obs_text = msg_text.strip() if isinstance(msg_text, str) else str(msg_text).strip()
                    if obs_text:
                        from llm import nlp_cognitive_stream
                        nlp_cognitive_stream.record_observation(username, obs_text)
                    if no_reply:
                        return ""

                    #确定是否命中q&a


                    answer, type = self.__get_answer(interact.interleaver, interact.data["msg"])


                    


                    #大语言模型回复    


                    text = ''


                    if answer is None or type != "qa":


                        if wsa_server.get_web_instance().is_connected(username):


                            wsa_server.get_web_instance().add_cmd({"panelMsg": "思考中...", "Username" : username, 'robot': f'{cfg.fay_url}/robot/Thinking.jpg'})


                        if wsa_server.get_instance().is_connected(username):


                            content = {'Topic': 'human', 'Data': {'Key': 'log', 'Value': "思考中..."}, 'Username' : username, 'robot': f'{cfg.fay_url}/robot/Thinking.jpg'}


                            wsa_server.get_instance().add_cmd(content)





                        from llm import nlp_cognitive_stream


                        text = nlp_cognitive_stream.question(interact.data["msg"], username, interact.data.get("observation", None))





                    else: 


                        text = answer


                        # 使用流式分割处理Q&A答案


                        self.__process_stream_output(text, username, session_type="qa", is_qa=True)


                           





                    return text      


                


                elif (index == 2):#透传模式：有音频则仅播音频；仅文本则流式+TTS


                    audio_url = interact.data.get("audio")


                    text = interact.data.get("text")





                    # 1) 存在音频：忽略文本，仅播放音频


                    if audio_url and str(audio_url).strip():


                        try:


                            audio_interact = Interact(


                                "stream", 1,


                                {"user": username, "msg": "", "isfirst": True, "isend": True, "audio": audio_url}


                            )


                            self.say(audio_interact, "")


                        except Exception:


                            pass


                        return 'success'





                    # 2) 只有文本：执行流式切分并TTS


                    if text and str(text).strip():


                        # 进行流式处理（用于TTS，流式处理中会记录到数据库）


                        self.__process_stream_output(text, username, f"type2_{interact.interleaver}", is_qa=False)


                        


                        # 不再需要额外记录，因为流式处理已经记录了


                        # self.__process_text_output(text, username, uid)


                        


                        return 'success'





                    # 没有有效内容


                    return 'success'


   


            except BaseException as e:


                print(e)


                return e


        else:


            return "还没有开始运行"





    #记录问答到log


    def write_to_file(self, path, filename, content):


        if not os.path.exists(path):


            os.makedirs(path)


        full_path = os.path.join(path, filename)


        with open(full_path, 'w', encoding='utf-8') as file:


            file.write(content)


            file.flush()  


            os.fsync(file.fileno()) 





    #触发交互


    def on_interact(self, interact: Interact):


        #创建用户


        username = interact.data.get("user", "User")


        if member_db.new_instance().is_username_exist(username)  == "notexists":


            member_db.new_instance().add_user(username)


        no_reply = interact.data.get("no_reply", False)

        if isinstance(no_reply, str):

            no_reply = no_reply.strip().lower() in ("1", "true", "yes", "y", "on")

        else:

            no_reply = bool(no_reply)



        if not no_reply:

            try:


                from utils.stream_state_manager import get_state_manager


                import uuid


                if get_state_manager().is_session_active(username):


                    stream_manager.new_instance().clear_Stream_with_audio(username)


                conv_id = "conv_" + str(uuid.uuid4())


                stream_manager.new_instance().set_current_conversation(username, conv_id)


                # 将当前会话ID附加到交互数据


                interact.data["conversation_id"] = conv_id


                # 允许新的生成


                stream_manager.new_instance().set_stop_generation(username, stop=False)


            except Exception:


                util.log(3, "开启新会话失败")





        if interact.interact_type == 1:


            MyThread(target=self.__process_interact, args=[interact]).start()


        else:


            return self.__process_interact(interact)





    #获取不同情绪声音


    def __get_mood_voice(self):


        voice = tts_voice.get_voice_of(config_util.config["attribute"]["voice"])


        if voice is None:


            voice = EnumVoice.XIAO_XIAO


        styleList = voice.value["styleList"]


        sayType = styleList["calm"]


        return sayType

    def __build_tts_cache_key(self, text, style):
        tts_module = str(getattr(cfg, "tts_module", "") or "")
        style_str = str(style or "")
        voice_name = ""
        try:
            voice_name = str(config_util.config.get("attribute", {}).get("voice", "") or "")
        except Exception:
            voice_name = ""
        if tts_module == "volcano":
            try:
                volcano_voice = str(getattr(cfg, "volcano_tts_voice_type", "") or "")
                if volcano_voice:
                    voice_name = volcano_voice
            except Exception:
                pass
        raw = f"{tts_module}|{voice_name}|{style_str}|{text}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def __get_tts_cache(self, key):
        with self.tts_cache_lock:
            file_url = self.tts_cache.get(key)
        if not file_url:
            return None
        if os.path.exists(file_url):
            return file_url
        with self.tts_cache_lock:
            if key in self.tts_cache:
                del self.tts_cache[key]
        return None

    def __set_tts_cache(self, key, file_url):
        if not file_url:
            return
        with self.tts_cache_lock:
            self.tts_cache[key] = file_url
            while len(self.tts_cache) > self.tts_cache_limit:
                try:
                    self.tts_cache.pop(next(iter(self.tts_cache)))
                except Exception:
                    break

    def __send_human_audio_ordered(self, content, username, conversation_id, conversation_msg_no, is_end=False):
        now = time.time()
        sent_messages = []
        data = content.get("Data", {}) if isinstance(content, dict) else {}
        has_audio_payload = bool(data.get("Value")) or bool(data.get("HttpValue"))
        is_end_marker_only = bool(is_end or data.get("IsEnd", 0)) and (not has_audio_payload)

        seq = None
        try:
            if conversation_msg_no is not None:
                seq = int(conversation_msg_no)
        except Exception:
            seq = None

        # Fallback to direct send for legacy paths without sequence metadata.
        if (not conversation_id) or (seq is None):
            if is_end_marker_only:
                return 0
            wsa_server.get_instance().add_cmd(content)
            return 1

        key = (username or "User", conversation_id)
        with self.human_audio_order_lock:
            state = self.human_audio_order_map.get(key)
            if state is None:
                state = {
                    "next_seq": None,
                    "buffer": {},
                    "last_progress_time": now,
                    "first_wait_start": now,
                    "start_known": False,
                    "end_seq": None,
                    "pending_end_seq": None,
                }
                self.human_audio_order_map[key] = state

            next_seq = state.get("next_seq")
            if (next_seq is not None) and (seq < next_seq):
                return 0

            def _mark_buffer_end(target_seq):
                existed = state["buffer"].get(target_seq)
                if isinstance(existed, dict):
                    existed_data = existed.get("Data", {})
                    if isinstance(existed_data, dict):
                        existed_data["IsEnd"] = 1
                    return True
                return False

            if is_end_marker_only:
                target_seq = None
                if seq in state["buffer"]:
                    target_seq = seq
                elif (seq - 1) in state["buffer"]:
                    target_seq = seq - 1
                elif state["buffer"]:
                    target_seq = max(state["buffer"].keys())

                if (target_seq is not None) and _mark_buffer_end(target_seq):
                    end_seq = state.get("end_seq")
                    state["end_seq"] = target_seq if end_seq is None else max(end_seq, target_seq)
                    state["pending_end_seq"] = None
                else:
                    state["pending_end_seq"] = seq
            else:
                if seq in state["buffer"]:
                    return 0
                state["buffer"][seq] = content

                pending_end_seq = state.get("pending_end_seq")
                if pending_end_seq is not None:
                    if (seq == pending_end_seq) or (seq == pending_end_seq - 1):
                        if _mark_buffer_end(seq):
                            end_seq = state.get("end_seq")
                            state["end_seq"] = seq if end_seq is None else max(end_seq, seq)
                            state["pending_end_seq"] = None

                if is_end:
                    end_seq = state.get("end_seq")
                    state["end_seq"] = seq if end_seq is None else max(end_seq, seq)

            is_first_flag = bool(data.get("IsFirst", 0))
            if (not state["start_known"]) and is_first_flag:
                state["start_known"] = True
                state["next_seq"] = seq
                state["last_progress_time"] = now
            elif (not state["start_known"]) and (seq == 0):
                state["start_known"] = True
                state["next_seq"] = 0
                state["last_progress_time"] = now
            elif (not state["start_known"]):
                first_elapsed = now - state.get("first_wait_start", now)
                if (first_elapsed >= self.human_audio_first_wait_seconds) and (0 in state["buffer"]):
                    state["start_known"] = True
                    state["next_seq"] = 0
                    state["last_progress_time"] = now

            def _flush_contiguous():
                flush_count = 0
                while (state["next_seq"] is not None) and (state["next_seq"] in state["buffer"]):
                    sent_messages.append(state["buffer"].pop(state["next_seq"]))
                    state["next_seq"] += 1
                    state["last_progress_time"] = now
                    flush_count += 1
                return flush_count

            _flush_contiguous()

            end_seq = state.get("end_seq")
            if (end_seq is not None) and (state.get("next_seq") is not None) and (state["next_seq"] > end_seq) and (not state["buffer"]):
                self.human_audio_order_map.pop(key, None)

        for message in sent_messages:
            wsa_server.get_instance().add_cmd(message)
        return len(sent_messages)

    def say(self, interact, text, type = ""):


        try:


            uid = member_db.new_instance().find_user(interact.data.get("user"))


            is_end = interact.data.get("isend", False)


            is_first = interact.data.get("isfirst", False)


            username = interact.data.get("user", "User")


            


            # 提前进行会话有效性与中断检查，避免产生多余面板/数字人输出


            try:


                user_for_stop = interact.data.get("user", "User")


                conv_id_for_stop = interact.data.get("conversation_id")


                if not is_end and stream_manager.new_instance().should_stop_generation(user_for_stop, conversation_id=conv_id_for_stop):


                    return None


            except Exception:


                pass


            


            #无效流式文本提前结束


            if not is_first and not is_end and (text is None or text.strip() == ""):


                return None


                


            # 检查是否是 prestart 内容（不应该影响 thinking 状态）


            is_prestart_content = self.__has_prestart(text)




            # 流式文本拼接存库


            content_id = 0


            # 使用 (username, conversation_id) 作为 key，避免并发会话覆盖


            conv = interact.data.get("conversation_id") or ""


            conv_map_key = (username, conv)





            if is_first == True:


                # reset any leftover think-mode at the start of a new reply


                # 但如果是 prestart 内容，不重置 thinking 状态


                try:


                    if uid is not None and not is_prestart_content:


                        self.think_mode_users[uid] = False


                        if uid in self.think_time_users:


                            del self.think_time_users[uid]
                        if uid in self.think_display_state:
                            del self.think_display_state[uid]


                except Exception:


                    pass


                # 如果没有 conversation_id，生成一个新的


                if not conv:


                    conv = "conv_" + str(uuid.uuid4())


                    conv_map_key = (username, conv)


                conv_no = 0


                # 创建第一条数据库记录，获得content_id


                if text and text.strip():


                    content_id, _ = content_db.new_instance().add_content('fay', 'speak', text, username, uid)


                else:


                    content_id, _ = content_db.new_instance().add_content('fay', 'speak', '', username, uid)





                # 保存content_id到会话映射中，使用 (username, conversation_id) 作为 key


                self.user_conv_map[conv_map_key] = {


                    "conversation_id": conv,


                    "conversation_msg_no": conv_no,


                    "content_id": content_id


                }


                util.log(1, f"流式会话开始: key={conv_map_key}, content_id={content_id}")


            else:


                # 获取之前保存的content_id


                conv_info = self.user_conv_map.get(conv_map_key, {})


                content_id = conv_info.get("content_id", 0)





                # 如果 conv_map_key 不存在，尝试使用 username 作为备用查找


                if not conv_info and text and text.strip():


                    # 查找所有匹配用户名的会话


                    for (u, c), info in list(self.user_conv_map.items()):


                        if u == username and info.get("content_id", 0) > 0:


                            content_id = info.get("content_id", 0)


                            conv_info = info
                            conv = info.get("conversation_id", c)
                            conv_map_key = (username, conv)


                            util.log(1, f"警告：使用备用会话 ({u}, {c}) 的 content_id={content_id}，原 key=({username}, {conv})")


                            break





                if conv_info:


                    conv_info["conversation_msg_no"] = conv_info.get("conversation_msg_no", 0) + 1





                # 如果有新内容，更新数据库


                if content_id > 0 and text and text.strip():


                    # 获取当前已有内容


                    existing_content = content_db.new_instance().get_content_by_id(content_id)


                    if existing_content:


                        # 累积内容


                        accumulated_text = existing_content[3] + text


                        update_ms = content_db.new_instance().update_content(content_id, accumulated_text)
                        if update_ms:
                            self._last_update_timetext = util.ms_to_timetext(update_ms)


                elif content_id == 0 and text and text.strip():


                    # content_id 为 0 表示可能会话 key 不匹配，记录警告


                    util.log(1, f"警告：content_id=0，无法更新数据库。user={username}, conv={conv}, text片段={text[:50] if len(text) > 50 else text}")





            # 固化当前会话序号，避免异步音频线程读取时会话映射已被清理而回落为0
            current_conv_info = self.user_conv_map.get(conv_map_key, {})
            if (not current_conv_info) and (not conv):
                for (u, c), info in list(self.user_conv_map.items()):
                    if u == username and info.get("conversation_id", ""):
                        current_conv_info = info
                        conv = info.get("conversation_id", c)
                        conv_map_key = (username, conv)
                        break
            if current_conv_info:
                interact.data["conversation_id"] = current_conv_info.get("conversation_id", conv)
                interact.data["conversation_msg_no"] = current_conv_info.get("conversation_msg_no", 0)
            else:
                if conv:
                    interact.data["conversation_id"] = conv
                interact.data["conversation_msg_no"] = interact.data.get("conversation_msg_no", 0)

            # 会话结束时清理 user_conv_map 中的对应条目，避免内存泄漏


            if is_end and conv_map_key in self.user_conv_map:


                del self.user_conv_map[conv_map_key]





            # 推送给前端和数字人


            try:


                user_for_stop = interact.data.get("user", "User")


                conv_id_for_stop = interact.data.get("conversation_id")


                if is_end or not stream_manager.new_instance().should_stop_generation(user_for_stop, conversation_id=conv_id_for_stop):


                    self.__process_text_output(text, interact.data.get('user'), uid, content_id, type, is_first, is_end)


            except Exception:


                self.__process_text_output(text, interact.data.get('user'), uid, content_id, type, is_first, is_end)


            


            # 处理think标签


            # 第一步：处理结束标记</think>


            if "</think>" in text:


                # 设置用户退出思考模式


                self.think_mode_users[uid] = False


                


                # 分割文本，提取</think>后面的内容


                # 如果有多个</think>，我们只关心最后一个后面的内容


                parts = text.split("</think>")


                text = parts[-1].strip()


                


                # 如果提取出的文本为空，则不需要继续处理


                if text == "":


                    return None


            # 第二步：处理开始标记<think>


            # 注意：这里要检查经过上面处理后的text


            if "<think>" in text:


                self.think_mode_users[uid] = True


                self.think_time_users[uid] = time.time()


   


            #”思考中“的输出


            if self.think_mode_users.get(uid, False):


                try:


                    user_for_stop = interact.data.get("user", "User")


                    conv_id_for_stop = interact.data.get("conversation_id")


                    should_block = stream_manager.new_instance().should_stop_generation(user_for_stop, conversation_id=conv_id_for_stop)


                except Exception:


                    should_block = False


                if not should_block:


                    if wsa_server.get_web_instance().is_connected(interact.data.get('user')):


                        wsa_server.get_web_instance().add_cmd({"panelMsg": "思考中...", "Username" : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Thinking.jpg'})


                    if wsa_server.get_instance().is_connected(interact.data.get("user")):


                        content = {'Topic': 'human', 'Data': {'Key': 'log', 'Value': "思考中..."}, 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Thinking.jpg'}


                        wsa_server.get_instance().add_cmd(content)





            #”请稍等“的音频输出（不影响文本输出）


            if self.think_mode_users.get(uid, False) == True and time.time() - self.think_time_users[uid] >= 5:


                self.think_time_users[uid] = time.time()


                text = "请稍等..."


            elif self.think_mode_users.get(uid, False) == True and "</think>" not in text:


                return None


            


            result = None


            audio_url = interact.data.get('audio', None)#透传的音频





            # 移除 prestart 标签内容，不进行TTS


            tts_text = self.__remove_prestart_tags(text) if text else text
            # 移除 markdown 图片语法，避免TTS朗读图片链接
            if tts_text:
                tts_text = re.sub(r'!\[.*?\]\(https?://[^\s\)]+\)', '', tts_text).strip()





            if audio_url is not None:#透传音频下载


                file_name = 'sample-' + str(int(time.time() * 1000)) + audio_url[-4:]


                result = self.download_wav(audio_url, './samples/', file_name)


            elif config_util.config["interact"]["playSound"] or wsa_server.get_instance().get_client_output(interact.data.get("user")) or self.__is_send_remote_device_audio(interact):#tts


                if tts_text != None and tts_text.replace("*", "").strip() != "":


                    # 检查是否需要停止TTS处理（按会话）


                    if stream_manager.new_instance().should_stop_generation(


                        interact.data.get("user", "User"),


                        conversation_id=interact.data.get("conversation_id")


                    ):


                        util.printInfo(1, interact.data.get('user'), 'TTS处理被打断，跳过音频合成')


                        return None





                    # 先过滤表情符号，然后再合成语音


                    filtered_text = self.__remove_emojis(tts_text.replace("*", ""))
                    filtered_text = self.__normalize_tts_text(filtered_text)


                    _lipsync_handles_audio = False  # khởi tạo trước khi vào block
                    if filtered_text is not None and filtered_text.strip() != "":


                        util.printInfo(1,  interact.data.get('user'), '合成音频...')


                        tm = time.time()


                        filtered_text = filtered_text.replace('\n', '')
                        mood_voice = self.__get_mood_voice()
                        cache_key = self.__build_tts_cache_key(filtered_text, mood_voice)
                        cache_result = self.__get_tts_cache(cache_key)
                        if cache_result is not None:
                            result = cache_result
                            util.printInfo(1, interact.data.get('user'), 'TTS cache hit')
                        else:
                            result = self.sp.to_sample(filtered_text, mood_voice)
                            self.__set_tts_cache(cache_key, result)

                        # Trigger lip sync avatar sau khi TTS tạo xong audio
                        # Nếu Wav2Lip khả dụng, nó sẽ handle audio — skip Fay audio pipeline
                        _lipsync_handles_audio = False
                        try:
                            from avatar import pipeline as avatar_pipeline
                            if result:
                                _lipsync_handles_audio = avatar_pipeline.on_audio_ready(result)
                        except Exception:
                            pass

                        # 合成完成后再次检查会话是否仍有效，避免继续输出旧会话结果


                        try:


                            user_for_stop = interact.data.get("user", "User")


                            conv_id_for_stop = interact.data.get("conversation_id")


                            if stream_manager.new_instance().should_stop_generation(user_for_stop, conversation_id=conv_id_for_stop):


                                return None


                        except Exception:


                            pass


                        util.printInfo(1,  interact.data.get("user"), "合成音频完成. 耗时: {} ms 文件:{}".format(math.floor((time.time() - tm) * 1000), result))


            else:


                # prestart 内容不应该触发机器人表情重置


                if is_end and not is_prestart_content and wsa_server.get_web_instance().is_connected(interact.data.get('user')):


                    wsa_server.get_web_instance().add_cmd({"panelMsg": "", 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Normal.jpg'})





            # 为数字人音频单独维护连续序号，避免 conversation_msg_no 因无音频片段产生空洞
            audio_conv_id = interact.data.get("conversation_id", "") or ""
            audio_conv_key = (username, audio_conv_id)
            audio_msg_no = None
            if result is not None:
                audio_msg_no = self.user_audio_conv_map.get(audio_conv_key, -1) + 1
                self.user_audio_conv_map[audio_conv_key] = audio_msg_no
            elif is_end:
                audio_msg_no = self.user_audio_conv_map.get(audio_conv_key, None)
                if audio_conv_key in self.user_audio_conv_map:
                    del self.user_audio_conv_map[audio_conv_key]
            interact.data["audio_conversation_msg_no"] = audio_msg_no
            if is_end and audio_conv_key in self.user_audio_conv_map:
                del self.user_audio_conv_map[audio_conv_key]

            if result is not None or is_first or is_end:


                # prestart 内容不需要进入音频处理流程


                if is_prestart_content:


                    return result


                if is_end:#TODO 临时方案：如果结束标记，则延迟1秒处理,免得is end比前面的音频tts要快


                    time.sleep(1)


                # Khi Wav2Lip handle audio, bỏ qua pipeline audio bình thường
                # để tránh phát âm thanh 2 lần (TTS ngay + lipsync video sau)
                if not _lipsync_handles_audio:
                    MyThread(target=self.__process_output_audio, args=[result, interact, text]).start()


                return result         


                


        except BaseException as e:


            print(e) 


        return None


    


    #下载wav


    def download_wav(self, url, save_directory, filename):


        try:


            # 发送HTTP GET请求以获取WAV文件内容


            if url is None:
                return None

            url = str(url).strip()
            if not url:
                return None

            if os.path.isfile(url):
                return url

            parsed_url = urlparse(url)
            if not parsed_url.scheme:
                if url.startswith('//'):
                    url = 'http:' + url
                else:
                    base_url = str(getattr(cfg, "fay_url", "") or "").strip()
                    if base_url:
                        url = urljoin(base_url.rstrip('/') + '/', url.lstrip('/'))

            response = requests.get(url, stream=True)


            response.raise_for_status()  # 检查请求是否成功





            # 确保保存目录存在


            if not os.path.exists(save_directory):


                os.makedirs(save_directory)





            # 构建保存文件的路径


            save_path = os.path.join(save_directory, filename)





            # 将WAV文件内容保存到指定文件


            with open(save_path, 'wb') as f:


                for chunk in response.iter_content(chunk_size=1024):


                    if chunk:


                        f.write(chunk)





            return save_path


        except requests.exceptions.RequestException as e:


            print(f"[Error] Failed to download file: {e}")


            return None








    #面板播放声音


    def __play_sound(self):


        try:


            import pygame


            pygame.mixer.init()  # 初始化pygame.mixer，只需要在此处初始化一次, 如果初始化失败，则不播放音频


        except Exception as e:


            util.printInfo(1, "System", "音频播放初始化失败,本机无法播放音频")


            return





        while self.__running:


            time.sleep(0.01)


            if not self.sound_query.empty():  # 如果队列不为空则播放音频


                file_url, audio_length, interact = self.sound_query.get()





                is_first = interact.data.get('isfirst') is True


                is_end = interact.data.get('isend') is True











                if file_url is not None:


                    util.printInfo(1, interact.data.get('user'), '播放音频...')





                    if is_first:


                        self.speaking = True


                    elif not is_end:


                        self.speaking = True





                #自动播报关闭


                global auto_play_lock


                global can_auto_play


                with auto_play_lock:


                    if self.timer is not None:


                        self.timer.cancel()


                        self.timer = None


                    can_auto_play = False





                if wsa_server.get_web_instance().is_connected(interact.data.get('user')):


                    wsa_server.get_web_instance().add_cmd({"panelMsg": "播放中 ...", "Username" : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Speaking.jpg'})





                if file_url is not None:


                    pygame.mixer.music.load(file_url)


                    pygame.mixer.music.play()





                    # 播放过程中计时，直到音频播放完毕


                    length = 0


                    while length < audio_length:


                        try:


                            user_for_stop = interact.data.get("user", "User")


                            conv_id_for_stop = interact.data.get("conversation_id")


                            if stream_manager.new_instance().should_stop_generation(user_for_stop, conversation_id=conv_id_for_stop):


                                try:


                                    pygame.mixer.music.stop()


                                except Exception:


                                    pass


                                break


                        except Exception:


                            pass


                        length += 0.01


                        time.sleep(0.01)





                if is_end:


                    self.play_end(interact)





                if wsa_server.get_web_instance().is_connected(interact.data.get('user')):


                    wsa_server.get_web_instance().add_cmd({"panelMsg": "", "Username" : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Normal.jpg'})


                # 播放完毕后通知


                if wsa_server.get_web_instance().is_connected(interact.data.get("user")):


                    wsa_server.get_web_instance().add_cmd({"panelMsg": "", 'Username': interact.data.get('user')})


    


    #推送远程音频


    def __send_remote_device_audio(self, file_url, interact):


        if file_url is None:


            return


        delkey = None    


        for key, value in fay_booter.DeviceInputListenerDict.items():


            if value.username == interact.data.get("user") and value.isOutput: #按username选择推送，booter.devicelistenerdice按用户名记录


                try:


                    value.deviceConnector.send(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08") # 发送音频开始标志，同时也检查设备是否在线


                    wavfile = open(os.path.abspath(file_url), "rb")


                    data = wavfile.read(102400)


                    total = 0


                    while data:


                        total += len(data)


                        value.deviceConnector.send(data)


                        data = wavfile.read(102400)


                        time.sleep(0.0001)


                    value.deviceConnector.send(b'\x08\x07\x06\x05\x04\x03\x02\x01\x00')# 发送音频结束标志


                    util.printInfo(1, value.username, "远程音频发送完成：{}".format(total))


                except socket.error as serr:


                    util.printInfo(1, value.username, "远程音频输入输出设备已经断开：{}".format(key)) 


                    value.stop()


                    delkey = key


        if delkey:


             value =  fay_booter.DeviceInputListenerDict.pop(delkey)


             if wsa_server.get_web_instance().is_connected(interact.data.get('user')):


                wsa_server.get_web_instance().add_cmd({"remote_audio_connect": False, "Username" : interact.data.get('user')})





    def __is_send_remote_device_audio(self, interact):


        for key, value in fay_booter.DeviceInputListenerDict.items():


            if value.username == interact.data.get("user") and value.isOutput:


                return True


        return False 





    #输出音频处理


    def __process_output_audio(self, file_url, interact, text):


        try:


            # 会话有效性与中断检查（最早返回，避免向面板/数字人发送任何旧会话输出）


            try:


                user_for_stop = interact.data.get("user", "User")


                conv_id_for_stop = interact.data.get("conversation_id")


                if stream_manager.new_instance().should_stop_generation(user_for_stop, conversation_id=conv_id_for_stop):


                    return


            except Exception:


                pass


            try:


                if file_url is None:


                    audio_length = 0


                elif file_url.endswith('.wav'):


                    audio = AudioSegment.from_wav(file_url)


                    audio_length = len(audio) / 1000.0  # 时长以秒为单位


                elif file_url.endswith('.mp3'):


                    audio = AudioSegment.from_mp3(file_url)


                    audio_length = len(audio) / 1000.0  # 时长以秒为单位


            except Exception as e:


                audio_length = 3





            #推送远程音频


            if file_url is not None:


                MyThread(target=self.__send_remote_device_audio, args=[file_url, interact]).start()       





            #发送音频给数字人接口


            if wsa_server.get_instance().get_client_output(interact.data.get("user")):


                # 使用 (username, conversation_id) 作为 key 获取会话信息


                audio_username = interact.data.get("user", "User")


                audio_conv_id = interact.data.get("conversation_id") or ""


                audio_conv_info = self.user_conv_map.get((audio_username, audio_conv_id), {})
                msg_no_from_interact = interact.data.get("audio_conversation_msg_no", None)
                conv_id_for_send = audio_conv_id if audio_conv_id else audio_conv_info.get("conversation_id", "")
                if msg_no_from_interact is None:
                    fallback_no = interact.data.get("conversation_msg_no", None)
                    if fallback_no is None:
                        conv_msg_no_for_send = audio_conv_info.get("conversation_msg_no", 0)
                    else:
                        conv_msg_no_for_send = fallback_no
                else:
                    conv_msg_no_for_send = msg_no_from_interact

                if file_url is not None:


                    content = {'Topic': 'human', 'Data': {'Key': 'audio', 'Value': os.path.abspath(file_url), 'HttpValue': f'{cfg.fay_url}/audio/' + os.path.basename(file_url),  'Text': text, 'Time': audio_length, 'Type': interact.interleaver, 'IsFirst': 1 if interact.data.get("isfirst", False) else 0,  'IsEnd': 1 if interact.data.get("isend", False) else 0, 'CONV_ID' : conv_id_for_send, 'CONV_MSG_NO' : conv_msg_no_for_send  }, 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Speaking.jpg'}


                    # 计算 Sentiment
                    sentiment_value = 0
                    try:
                        if cfg.baidu_emotion_api_key and cfg.baidu_emotion_secret_key:
                            sentiment_value = baidu_emotion.get_sentiment(text)
                            util.printInfo(1, interact.data.get("user"), f"百度情感分析: {sentiment_value} (文本: {text[:20]}...)")
                        else:
                            sentiment_value = self.__analyze_sentiment_by_keywords(text)
                            util.printInfo(1, interact.data.get("user"), f"关键词情感分析: {sentiment_value} (文本: {text[:20]}...)")
                    except Exception as sentiment_error:
                        util.printInfo(1, interact.data.get("user"), f"情感分析失败: {sentiment_error}，使用关键词匹配")
                        sentiment_value = self.__analyze_sentiment_by_keywords(text)

                    content["Data"]["Sentiment"] = sentiment_value

                    # 提取文本中的 markdown 图片 URL 并附加到消息
                    audio_image_urls = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', text or "")
                    if audio_image_urls:
                        content["Data"]["Images"] = audio_image_urls
                        # 从 Text 中移除图片语法，避免语音朗读图片链接
                        content["Data"]["Text"] = re.sub(r'!\[.*?\]\(https?://[^\s\)]+\)', '', text).strip()

                    # 计算 Action
                    action_signal = resolve_action_signal(text)
                    if action_signal:
                        content["Data"]["Action"] = action_signal
                        util.printInfo(1, interact.data.get("user"), f"通用动作触发: {action_signal.get('code')}")

                    #计算lips


                    if platform.system() == "Windows":


                        try:


                            lip_sync_generator = LipSyncGenerator()


                            viseme_list = lip_sync_generator.generate_visemes(os.path.abspath(file_url))


                            consolidated_visemes = lip_sync_generator.consolidate_visemes(viseme_list)


                            content["Data"]["Lips"] = consolidated_visemes


                        except Exception as e:


                            print(e)


                            util.printInfo(1, interact.data.get("user"),  "唇型数据生成失败")


                    sent_count = self.__send_human_audio_ordered(
                        content,
                        audio_username,
                        conv_id_for_send,
                        conv_msg_no_for_send,
                        is_end=bool(interact.data.get("isend", False)),
                    )
                    if sent_count > 0:
                        util.printInfo(1, interact.data.get("user"), "digital human audio sent")
                    else:
                        util.printInfo(1, interact.data.get("user"), "digital human audio queued")
                elif bool(interact.data.get("isend", False)):
                    # 没有音频文件时，也要给数字人发送结束标记，避免客户端一直等待
                    end_target_seq = conv_msg_no_for_send
                    try:
                        end_target_seq = int(conv_msg_no_for_send)
                    except Exception:
                        end_target_seq = conv_msg_no_for_send
                    end_content = {
                        'Topic': 'human',
                        'Data': {
                            'Key': 'audio',
                            'Value': '',
                            'HttpValue': '',
                            'Text': text,
                            'Time': 0,
                            'Type': interact.interleaver,
                            'IsFirst': 1 if interact.data.get("isfirst", False) else 0,
                            'IsEnd': 1,
                            'CONV_ID': conv_id_for_send,
                            'CONV_MSG_NO': end_target_seq
                        },
                        'Username': interact.data.get('user'),
                        'robot': f'{cfg.fay_url}/robot/Speaking.jpg'
                    }
                    sent_count = self.__send_human_audio_ordered(
                        end_content,
                        audio_username,
                        conv_id_for_send,
                        end_target_seq,
                        is_end=True,
                    )
                    if sent_count > 0:
                        util.printInfo(1, interact.data.get("user"), "digital human audio end sent")
                    else:
                        util.printInfo(1, interact.data.get("user"), "digital human audio end queued")





            #面板播放


            config_util.load_config()


            # 检查是否是 prestart 内容


            is_prestart = self.__has_prestart(text)

            if config_util.config["interact"]["playSound"]:


                # prestart 内容不应该进入播放队列，避免触发 Normal 状态


                if not is_prestart:


                    self.sound_query.put((file_url, audio_length, interact))


            else:


                # prestart 内容不应该重置机器人表情


                if not is_prestart and wsa_server.get_web_instance().is_connected(interact.data.get('user')):


                    wsa_server.get_web_instance().add_cmd({"panelMsg": "", 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Normal.jpg'})


            


        except Exception as e:


            print(e)





    def play_end(self, interact):


        self.speaking = False


        global can_auto_play


        global auto_play_lock


        with auto_play_lock:


            if self.timer:


                self.timer.cancel()


                self.timer = None


            if interact.interleaver != 'auto_play': #交互后暂停自动播报30秒


                self.timer = threading.Timer(30, self.set_auto_play)


                self.timer.start()


            else:


                can_auto_play = True





    #恢复自动播报(如果有)   


    def set_auto_play(self):


        global auto_play_lock


        global can_auto_play


        with auto_play_lock:


            can_auto_play = True


            self.timer = None





    #启动核心服务


    def start(self):


        MyThread(target=self.__play_sound).start()





    #停止核心服务


    def stop(self):


        self.__running = False


        self.speaking = False


        self.sp.close()


        wsa_server.get_web_instance().add_cmd({"panelMsg": ""})


        content = {'Topic': 'human', 'Data': {'Key': 'log', 'Value': ""}}


        wsa_server.get_instance().add_cmd(content)





    def __record_response(self, text, username, uid):


        """


        记录AI的回复内容


        :param text: 回复文本


        :param username: 用户名


        :param uid: 用户ID


        :return: content_id


        """


        self.write_to_file("./logs", "answer_result.txt", text)


        content_id, _ = content_db.new_instance().add_content('fay', 'speak', text, username, uid)
        return content_id





    def __remove_prestart_tags(self, text):


        """


        移除文本中的 prestart 标签及其内容


        :param text: 原始文本


        :return: 移除 prestart 标签后的文本


        """


        if not text:


            return text


        import re


        # 移除 <prestart ...>...</prestart> 标签及其内容（支持属性）

        cleaned = re.sub(r'<prestart[^>]*>[\s\S]*?</prestart>', '', text, flags=re.IGNORECASE)

        return cleaned.strip()


    def __remove_think_tags(self, text):
        """
        移除文本中的 think 标签及其内容（含未闭合的流式分片）

        :param text: 原始文本
        :return: 移除 think 标签后的文本
        """
        if not text:
            return text

        # 1. 先剥离完整的 <think>...</think>
        cleaned = re.sub(r'<think[^>]*>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)

        # 2. 处理流式分片中孤立的 </think> —— 取最后一个 </think> 之后的内容
        if re.search(r'</think>', cleaned, flags=re.IGNORECASE):
            cleaned = re.split(r'</think>', cleaned, flags=re.IGNORECASE)[-1]

        # 3. 处理流式分片中未闭合的 <think>... —— 截断该位置之后的内容
        if re.search(r'<think[^>]*>', cleaned, flags=re.IGNORECASE):
            cleaned = re.split(r'<think[^>]*>', cleaned, flags=re.IGNORECASE)[0]

        return cleaned.strip()



    def __has_prestart(self, text):

        """

        判断文本中是否包含 prestart 标签（支持属性）

        """

        if not text:

            return False

        return re.search(r'<prestart[^>]*>[\s\S]*?</prestart>', text, flags=re.IGNORECASE) is not None





    def __truncate_think_for_panel(self, text, uid, username):

        if not text or not isinstance(text, str):

            return text

        key = uid if uid is not None else username

        state = self.think_display_state.get(key)

        if state is None:

            state = {"in_think": False, "in_tool_output": False, "tool_count": 0, "tool_truncated": False}

            self.think_display_state[key] = state

        if not state["in_think"] and "<think>" not in text and "</think>" not in text:

            return text

        tool_output_regex = re.compile(r"\[TOOL\]\s*(?:Output|\u8f93\u51fa)[:\uff1a]", re.IGNORECASE)

        section_regex = re.compile(r"(?i)(^|[\r\n])(\[(?:TOOL|PLAN)\])")

        out = []

        i = 0

        while i < len(text):

            if not state["in_think"]:

                idx = text.find("<think>", i)

                if idx == -1:

                    out.append(text[i:])

                    break

                out.append(text[i:idx + len("<think>")])

                state["in_think"] = True

                i = idx + len("<think>")

                continue

            if not state["in_tool_output"]:

                think_end = text.find("</think>", i)

                tool_match = tool_output_regex.search(text, i)

                next_pos = None

                next_kind = None

                if tool_match:

                    next_pos = tool_match.start()

                    next_kind = "tool"

                if think_end != -1 and (next_pos is None or think_end < next_pos):

                    next_pos = think_end

                    next_kind = "think_end"

                if next_pos is None:

                    out.append(text[i:])

                    break

                if next_pos > i:

                    out.append(text[i:next_pos])

                if next_kind == "think_end":

                    out.append("</think>")

                    state["in_think"] = False

                    state["in_tool_output"] = False

                    state["tool_count"] = 0

                    state["tool_truncated"] = False

                    i = next_pos + len("</think>")

                else:

                    marker_end = tool_match.end()

                    out.append(text[next_pos:marker_end])

                    state["in_tool_output"] = True

                    state["tool_count"] = 0

                    state["tool_truncated"] = False

                    i = marker_end

                continue

            think_end = text.find("</think>", i)

            section_match = section_regex.search(text, i)

            end_pos = None

            if section_match:

                end_pos = section_match.start(2)

            if think_end != -1 and (end_pos is None or think_end < end_pos):

                end_pos = think_end

            segment = text[i:] if end_pos is None else text[i:end_pos]

            if segment:

                if state["tool_truncated"]:

                    pass

                else:

                    remaining = self.think_display_limit - state["tool_count"]

                    if remaining <= 0:

                        out.append("...")

                        state["tool_truncated"] = True

                    elif len(segment) <= remaining:

                        out.append(segment)

                        state["tool_count"] += len(segment)

                    else:

                        out.append(segment[:remaining] + "...")

                        state["tool_count"] += remaining

                        state["tool_truncated"] = True

            if end_pos is None:

                break

            state["in_tool_output"] = False

            state["tool_count"] = 0

            state["tool_truncated"] = False

            i = end_pos

        return "".join(out)

    def __send_panel_message(self, text, username, uid, content_id=None, type=None, is_end=False):


        """


        发送消息到Web面板


        :param text: 消息文本


        :param username: 用户名


        :param uid: 用户ID


        :param content_id: 内容ID


        :param type: 消息类型


        """


        if not wsa_server.get_web_instance().is_connected(username):


            return





        # 检查是否是 prestart 内容，prestart 内容不应该更新日志区消息


        # 因为这会覆盖掉"思考中..."的状态显示


        is_prestart = self.__has_prestart(text)
        display_text = self.__truncate_think_for_panel(text, uid, username)




        # gui日志区消息（prestart 内容跳过，保持"思考中..."状态）


        if not is_prestart:


            wsa_server.get_web_instance().add_cmd({


                "panelMsg": display_text,


                "Username": username


            })


        


        # 聊天窗消息


        if content_id is not None:


            wsa_server.get_web_instance().add_cmd({


                "panelReply": {


                    "type": "fay",


                    "content": display_text,


                    "username": username,


                    "uid": uid,


                    "id": content_id,


                    "is_adopted": type == 'qa',


                    "timetext": getattr(self, '_last_update_timetext', None) or util.get_time_ms(),


                    "is_end": is_end


                },


                "Username": username


            })





    def __send_digital_human_message(self, text, username, is_first=False, is_end=False):


        """


        发送消息到数字人（语音应该在say方法驱动数字人输出）


        :param text: 消息文本


        :param username: 用户名


        :param is_first: 是否是第一段文本


        :param is_end: 是否是最后一段文本


        """


        # 从原始文本中提取 markdown 图片 URL（在清理前提取）
        image_urls = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', text or "")

        # 移除 prestart 与 think 标签内容，不发送给数字人


        cleaned_text = self.__remove_prestart_tags(text) if text else ""

        cleaned_text = self.__remove_think_tags(cleaned_text) if cleaned_text else ""


        full_text = self.__remove_emojis(cleaned_text.replace("*", "")) if cleaned_text else ""


        # 从清理后的文本中移除 markdown 图片语法，避免数字人语音朗读图片链接
        if image_urls:
            full_text = re.sub(r'!\[.*?\]\(https?://[^\s\)]+\)', '', full_text).strip()


        # 如果文本为空且不是结束标记，则不发送，但需保留 is_first

        if not full_text and not is_end:

            if is_first:

                self.pending_isfirst[username] = True

            return



        # 检查是否有延迟的 is_first 需要应用

        if self.pending_isfirst.get(username, False):

            is_first = True

            self.pending_isfirst[username] = False




        if wsa_server.get_instance().is_connected(username):


            content = {


                'Topic': 'human',


                'Data': {


                    'Key': 'text',


                    'Value': full_text,


                    'IsFirst': 1 if is_first else 0,


                    'IsEnd': 1 if is_end else 0


                },


                'Username': username


            }

            if image_urls:
                content['Data']['Images'] = image_urls


            wsa_server.get_instance().add_cmd(content)





    def __process_text_output(self, text, username, uid, content_id, type, is_first=False, is_end=False):


        """


        完整文本输出到各个终端


        :param text: 主要回复文本


        :param textlist: 额外回复列表


        :param username: 用户名


        :param uid: 用户ID


        :param type: 消息类型


        :param is_first: 是否是第一段文本


        :param is_end: 是否是最后一段文本


        """


        if text:


            text = text.strip()


            


        # 记录主回复


        # content_id = self.__record_response(text, username, uid)


        


        # 发送主回复到面板和数字人


        self.__send_panel_message(text, username, uid, content_id, type, is_end)


        self.__send_digital_human_message(text, username, is_first, is_end)


        


        # 打印日志


        util.printInfo(1, username, '({}) {}'.format("llm", text))


    def __analyze_sentiment_by_keywords(self, text):
        """基于关键词的简单情感分析
        返回: -2 ~ +2 的情感值
        """
        # 积极关键词 - 非常积极（+2）
        very_positive_keywords = [
            '开心', '高兴', '喜欢', '爱', '太好了', '棒', '优秀', '成功',
            '快乐', '幸福', '满足', '谢谢', '感谢', '赞', '哈哈', '笑',
            '太棒了', '厉害', '赢了', '庆祝', '欢呼', '耶', '万岁',
            '完美', '绝妙', '精彩', '激动', '兴奋', '荣幸', '乐意'
        ]

        # 积极关键词 - 轻微积极（+1）
        positive_keywords = [
            '好', '对', '是', 'yes', '好的', '可以', '没问题', '明白',
            '当然', '没错', '正确', '同意', '行', '嗯', '哦~', '呀',
            '呢', '～', '噗嗤', '嘿嘿', '嘻嘻', '哈哈', '呀~', '呢~',
            '欢迎', '请进', '请', '荣幸', '乐意', '愿意', '想要'
        ]

        # 消极关键词 - 轻微消极（-1）
        negative_keywords = [
            '不好', '差', '错', '糟糕', '失败', '失望', '生气',
            '不', 'no', '不要', '不行', '不能', '别', '不是',
            '难过', '烦', '烦人', '讨厌', '唉', '可是', '但是',
            '不过', '只是', '担心', '害怕', '紧张'
        ]

        # 消极关键词 - 非常消极（-2）
        very_negative_keywords = [
            '难过', '伤心', '痛苦', '悲伤', '哭', '恨',
            '愤怒', '滚', '完蛋', '绝望', '崩溃', '痛苦',
            '讨厌死', '恨死', '气死', '烦死', '糟糕透顶'
        ]

        # 统计匹配的关键词数量
        very_positive_count = sum(1 for kw in very_positive_keywords if kw in text)
        positive_count = sum(1 for kw in positive_keywords if kw in text)
        negative_count = sum(1 for kw in negative_keywords if kw in text)
        very_negative_count = sum(1 for kw in very_negative_keywords if kw in text)

        # 计算情感值
        sentiment = (very_positive_count * 2 + positive_count * 1 -
                     negative_count * 1 - very_negative_count * 2)

        # 限制在 -2 ~ +2 范围内
        if sentiment > 2:
            sentiment = 2
        elif sentiment < -2:
            sentiment = -2

        # 标点符号和语气分析
        if '？' in text or '!' in text or '~' in text:
            sentiment += 0.3
        if '...' in text or '。。.' in text:
            sentiment -= 0.3

        # 再次限制范围
        if sentiment > 2:
            sentiment = 2
        elif sentiment < -2:
            sentiment = -2

        return sentiment



import importlib


fay_booter = importlib.import_module('fay_booter')





