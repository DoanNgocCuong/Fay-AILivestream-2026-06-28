class FayInterface {
    constructor(baseWsUrl, baseApiUrl, vueInstance) {
        this.baseWsUrl = baseWsUrl;
        this.baseApiUrl = baseApiUrl;
        this.websocket = null;
        this.vueInstance = vueInstance; 
    }

    connectWebSocket() {
        if (this.websocket) {
            this.websocket.onopen = null;
            this.websocket.onmessage = null;
            this.websocket.onclose = null;
            this.websocket.onerror = null;
        }

        this.websocket = new WebSocket(this.baseWsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connection opened');
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleIncomingMessage(data);
        };

        this.websocket.onclose = () => {
            console.log('WebSocket connection closed. Attempting to reconnect...');
            setTimeout(() => this.connectWebSocket(), 5000); 
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    async fetchData(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching data:', error);
            return null;
        }
    }

    getData() {
        return this.fetchData(`${this.baseApiUrl}/api/get-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
    }

    submitConfig(config) {
        return this.fetchData(`${this.baseApiUrl}/api/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config }),
        });
    }

    startLive() {
        return this.fetchData(`${this.baseApiUrl}/api/start-live`, {
            method: 'POST',
        });
    }

    stopLive() {
        return this.fetchData(`${this.baseApiUrl}/api/stop-live`, {
            method: 'POST',
        });
    }

    getRunStatus() {
        return this.fetchData(`${this.baseApiUrl}/api/get-run-status`, {
          method: 'POST'
        });
      }
  

    handleIncomingMessage(data) {
        const vueInstance = this.vueInstance; 
        console.log('Incoming message:', data);
        if (data.liveState !== undefined) {
            vueInstance.liveState = data.liveState;
            if (data.liveState === 1) {
                vueInstance.configEditable = false;
            } else if (data.liveState === 0) {
                vueInstance.configEditable = true;
            }
        }

        if (data.voiceList !== undefined) {
            vueInstance.voiceList = data.voiceList.map((voice) => ({
                value: voice.id,
                label: voice.name,
            }));
        }
        if (data.robot) {
            console.log(data.robot);
            vueInstance.$set(vueInstance, 'robot', data.robot);
        }

        if (data.is_connect !== undefined) {
            vueInstance.isConnected = data.is_connect;
        }

        if (data.remote_audio_connect !== undefined) {
            vueInstance.remoteAudioConnected = data.remote_audio_connect;
        }
    }
}

new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data() {
        return {
            hostname: window.location.hostname,
            base_url: window.location.origin,
            messages: [],
            newMessage: '',
            fayService: null,
            liveState: 0,
            isConnected: false,
            remoteAudioConnected: false,
            userList: [],
            selectedUser: null,
            loading: false,
            chatMessages: {},
            panelMsg: '',
            panelReply: '',
            robot: 'images/emoji.png',
            configEditable: true,
            source_liveRoom_url: '',
            play_sound_enabled: false,
            mcpOnlineStatus: false,
            mcpCheckTimer: null,
            visualization_detection_enabled: false,
            source_record_enabled: false,
            source_record_device: '',
            attribute_name: "",
            attribute_gender: "",
            attribute_age: "",
            attribute_birth: "",
            attribute_zodiac: "",
            attribute_constellation: "",
            attribute_job: "",
            attribute_additional: "", 
            attribute_contact: "",
            attribute_voice: "",
            attribute_position: "",
            attribute_goal: "",
            QnA:"",
            interact_perception_gift: 0,
            interact_perception_follow: 0,
            interact_perception_join: 0,
            interact_perception_chat: 0,
            interact_perception_indifferent: 0,
            interact_maxInteractTime: 15,
            voiceList: [],
            deviceList: [],
            wake_word_enabled:false,
            wake_word: '',
            loading: false,
            remote_audio_connect: false,
            wake_word_type: 'common',
            wake_word_type_options: [{
                value: 'common',
                label: 'Thông thường'
            }, {
                value: 'front',
                label: 'Từ đứng trước'
            }],
            automatic_player_status: false,
            automatic_player_url: "",
            host_url: window.location.protocol + '//' + window.location.hostname + ':' + window.location.port,
            memory_isolate_by_user: false,
            use_bionic_memory: false,
        };
    },
    created() {
        this.initFayService();
        this.getData();
        this.checkMcpStatus();
        this.startMcpStatusTimer();
    },
    methods: {
        initFayService() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws';
            const wsHost = window.location.hostname;
            this.fayService = new FayInterface(`${wsProtocol}://${wsHost}:10003`, this.host_url, this);
            this.fayService.connectWebSocket();
        },
        getData() {
            this.fayService.getRunStatus().then((data) => {
                if (data) {
                    if(data.status){
                        this.liveState = 1;
                        this.configEditable = false;
                    }else{
                        this.liveState = 0;
                        this.configEditable = true;
                    }
                    
                }
            });
            this.fayService.getData().then((data) => {
                if (data) {
                    this.voiceList =  data.voice_list.map((voice) => ({
                        value: voice.id,
                        label: voice.name,
                    }));
                    this.updateConfigFromData(data.config);
                }
            });
        },
        updateConfigFromData(config) {
          
            if (config.interact) {
                this.play_sound_enabled = config.interact.playSound;
                this.visualization_detection_enabled = config.interact.visualization;
                this.QnA = config.interact.QnA;
            }
            if (config.source && config.source.record) {
                this.source_record_enabled = config.source.record.enabled;
                this.source_record_device = config.source.record.device;
                this.wake_word = config.source.wake_word;
                this.wake_word_type = config.source.wake_word_type;
                this.wake_word_enabled = config.source.wake_word_enabled;
                this.automatic_player_status = config.source.automatic_player_status;
                this.automatic_player_url = config.source.automatic_player_url;

            }
            if (config.attribute) {
                this.attribute_name = config.attribute.name;
                this.attribute_gender = config.attribute.gender;
                this.attribute_age = config.attribute.age;
                this.attribute_name = config.attribute.name;
                this.attribute_gender = config.attribute.gender;
                this.attribute_birth = config.attribute.birth;
                this.attribute_zodiac = config.attribute.zodiac;
                this.attribute_constellation = config.attribute.constellation;
                this.attribute_job = config.attribute.job;
                this.attribute_additional = config.attribute.additional; 
                this.attribute_contact = config.attribute.contact;
                this.attribute_voice = config.attribute.voice;
                this.attribute_position = config.attribute.position || "销售";
                this.attribute_goal = config.attribute.goal || "促成交易";
            }
            if (config.interact.perception) {
                this.interact_perception_follow = config.interact.perception.follow;
            }
            if (config.memory) {
                this.memory_isolate_by_user = config.memory.isolate_by_user || false;
            }
            // Bionic memory switch removed from UI; force disabled
            this.use_bionic_memory = false;
        },
        saveConfig() {
            let url = `${this.host_url}/api/submit`;
            let send_data = {
                "config": {
                    "source": {
                        "liveRoom": {
                            "enabled": this.configEditable,
                            "url": this.source_liveRoom_url
                        },
                        "record": {
                            "enabled": this.source_record_enabled,
                            "device": this.source_record_device
                        },
                        "wake_word_enabled": this.wake_word_enabled,
                        "wake_word": this.wake_word,
                        "wake_word_type": this.wake_word_type,
                        "automatic_player_status": this.automatic_player_status,
                        "automatic_player_url": this.automatic_player_url
                    },
                    "attribute": {
                        "voice": this.attribute_voice,
                        "name": this.attribute_name,
                        "gender": this.attribute_gender,
                        "age": this.attribute_age,
                        "birth": this.attribute_birth,
                        "zodiac": this.attribute_zodiac,
                        "constellation": this.attribute_constellation,
                        "job": this.attribute_job,
                        "additional": this.attribute_additional, 
                        "contact": this.attribute_contact,
                        "position": this.attribute_position, 
                        "goal": this.attribute_goal, 
                    },
                    "interact": {
                        "playSound": this.play_sound_enabled,
                        "visualization": this.visualization_detection_enabled,
                        "QnA": this.QnA,
                        "perception": {
                            "follow": this.interact_perception_follow
                        },
                        "maxInteractTime": this.interact_maxInteractTime
                    },
                    "memory": {
                        "isolate_by_user": this.memory_isolate_by_user,
                        "use_bionic_memory": false
                    },
                    "items": []
                }
            };

            let xhr = new XMLHttpRequest()
            xhr.open("post", url)
            xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded")
            xhr.send('data=' + JSON.stringify(send_data))
            let executed = false
            xhr.onreadystatechange = async function () {
                if (!executed && xhr.status === 200) {
                    try {
                        let data = await eval('(' + xhr.responseText + ')')
                        console.log("data: " + data['result'])
                        executed = true
                    } catch (e) {
                    }
                }
            }
            this.sendSuccessMsg("Đã lưu cấu hình!");
        },
        startLive() {
            this.liveState = 2
            this.fayService.startLive().then(() => {
                this.configEditable = false;
                this.sendSuccessMsg('Đã bật!');
            });
        },
        stopLive() {
            this.liveState = 3
            this.fayService.stopLive().then(() => {
                this.configEditable = true;
                this.sendSuccessMsg('Đã tắt!');
            });
        },
        sendSuccessMsg(message) {
            this.$notify({
                title: 'Thành công',
                message,
                type: 'success',
            });
        },
        clearMemory() {
            this.$confirm('Thao tác này sẽ xoá toàn bộ bộ nhớ hội thoại của Fay. Cần khởi động lại ứng dụng để áp dụng. Bạn có chắc chắn muốn tiếp tục?', 'Xác nhận', {
                confirmButtonText: 'Đồng ý',
                cancelButtonText: 'Huỷ',
                type: 'warning'
            }).then(() => {
                fetch(`${this.host_url}/api/clear-memory`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.sendSuccessMsg(data.message || "Đã xoá bộ nhớ, vui lòng khởi động lại ứng dụng");
                    } else {
                        this.$notify({
                            title: 'Lỗi',
                            message: data.message || 'Xoá bộ nhớ thất bại',
                            type: 'error'
                        });
                    }
                })
                .catch(error => {
                    this.$notify({
                        title: 'Lỗi',
                        message: 'Yêu cầu xoá bộ nhớ thất bại',
                        type: 'error'
                    });
                });
            }).catch(() => {});
        },
        clonePersonality() {
            if (this.use_bionic_memory) {
                this.$notify({
                    title: 'Thông báo',
                    message: 'Chế độ bộ nhớ sinh học không hỗ trợ sao chép tính cách. Vui lòng tắt chế độ này trước.',
                    type: 'warning'
                });
                return;
            }

            if (this.liveState === 1) {
                this.$prompt('Nhập yêu cầu sao chép', 'Sao chép tính cách', {
                    confirmButtonText: 'Đồng ý',
                    cancelButtonText: 'Huỷ',
                    inputPlaceholder: 'Ví dụ: Bạn là một trợ lý bán hàng nhiệt tình và thân thiện...'
                }).then(({ value }) => {
                    if (!value) {
                        this.$notify({
                            title: 'Thông báo',
                            message: 'Yêu cầu sao chép không được để trống',
                            type: 'warning'
                        });
                        return;
                    }
                    fetch(`${this.host_url}/api/start-genagents`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ instruction: value })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            this.$alert(`Trang phân tích đã khởi động. Vui lòng copy link sau và mở trong cửa sổ mới:<br><br><code style="background-color: #f5f5f5; padding: 5px; border-radius: 3px;">${data.url}</code>`, 'Sao chép tính cách', {
                                confirmButtonText: 'OK',
                                dangerouslyUseHTMLString: true
                            });
                        } else {
                            this.$notify({
                                title: 'Lỗi',
                                message: data.message || 'Khởi động trang phân tích thất bại',
                                type: 'error'
                            });
                        }
                    })
                    .catch(error => {
                        this.$notify({
                            title: 'Lỗi',
                            message: 'Yêu cầu khởi động trang phân tích thất bại',
                            type: 'error'
                        });
                    });
                });
            } else {
                this.$notify({
                    title: 'Thông báo',
                    message: 'Vui lòng bật Fay trước khi thực hiện thao tác này',
                    type: 'warning'
                });
            }
        },
        
        // 检查MCP服务器状态
        checkMcpStatus() {
            const mcpUrl = `http://${this.hostname}:5010/api/mcp/servers`;
            
            // 使用超时设置的fetch请求
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3秒超时
            
            fetch(mcpUrl, { signal: controller.signal })
                .then(response => {
                    clearTimeout(timeoutId);
                    if (!response.ok) {
                        throw new Error('MCP服务器响应不正常');
                    }
                    return response.json();
                })
                .then(data => {
                    if (Array.isArray(data)) {
                        // 检查是否有任何一个MCP服务器在线
                        const hasOnlineServer = data.some(server => server.status === 'online');
                        this.mcpOnlineStatus = hasOnlineServer;
                    } else {
                        console.warn('MCP服务器返回的数据格式不正确');
                        this.mcpOnlineStatus = false;
                    }
                })
                .catch(error => {
                    clearTimeout(timeoutId);
                    // 如果是超时错误，不输出详细错误信息
                    if (error.name === 'AbortError') {
                        console.warn('MCP服务器请求超时');
                    } else {
                        console.warn('检查MCP状态出错:', error.message);
                    }
                    this.mcpOnlineStatus = false;
                });
        },
        
        // 启动MCP状态检查定时器
        startMcpStatusTimer() {
            // 清除可能存在的旧定时器
            if (this.mcpCheckTimer) {
                clearInterval(this.mcpCheckTimer);
            }
            // 设置新的定时器，每30秒检查一次MCP状态
            this.mcpCheckTimer = setInterval(() => {
                this.checkMcpStatus();
            }, 30000);
        },

        // 仿生记忆开关变化事件处理
        onBionicMemoryChange(value) {
            if (value) {
                this.$confirm('Bật bộ nhớ sinh học sẽ sử dụng hệ thống bộ nhớ khác. Chức năng sao chép tính cách và tách biệt nhận thức sẽ không khả dụng. Bạn có chắc chắn muốn bật?', 'Xác nhận', {
                    confirmButtonText: 'Đồng ý',
                    cancelButtonText: 'Huỷ',
                    type: 'warning'
                }).then(() => {
                    this.saveConfig();
                }).catch(() => {
                    this.use_bionic_memory = false;
                });
            } else {
                this.saveConfig();
            }
        },
    },
});
