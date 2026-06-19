/** @odoo-module **/
import { Component, useState, useRef, onMounted, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AIChatbotClientAction extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.messagesRef = useRef("messagesContainer");
        this._localCounter = 0;

        this.state = useState({
            sessions: [],
            currentSessionId: null,
            messages: [],
            inputText: "",
            isLoading: false,
            pendingAction: null, // {id, summary, action_type}
            error: null,
            sidebarOpen: true,
        });

        onWillStart(async () => {
            await this.loadSessions();
            if (this.state.sessions.length) {
                await this.switchSession(this.state.sessions[0].id);
            } else {
                await this.createSession();
            }
        });

        onMounted(() => {
            this.scrollToBottom();
        });
    }

    _nextLocalId() {
        this._localCounter += 1;
        return "local_" + this._localCounter;
    }

    async loadSessions() {
        try {
            const res = await this.rpc("/ai_chatbot/get_sessions", {});
            if (res && res.success) {
                this.state.sessions = res.sessions || [];
            }
        } catch (e) {
            this.state.error = "Không tải được danh sách phiên chat.";
        }
    }

    async createSession() {
        try {
            const res = await this.rpc("/ai_chatbot/create_session", {});
            if (res && res.success) {
                this.state.sessions.unshift({
                    id: res.session_id,
                    name: res.name,
                    last_message: "",
                    message_count: 0,
                    write_date: "",
                });
                this.state.currentSessionId = res.session_id;
                this.state.messages = [];
                this.state.pendingAction = null;
            }
        } catch (e) {
            this.state.error = "Không tạo được phiên chat mới.";
        }
    }

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }

    async switchSession(sessionId) {
        this.state.currentSessionId = sessionId;
        this.state.pendingAction = null;
        await this.loadMessages(sessionId);
    }

    async loadMessages(sessionId) {
        try {
            const res = await this.rpc("/ai_chatbot/get_messages", { session_id: sessionId });
            if (res && res.success) {
                this.state.messages = (res.messages || []).map((m) => ({
                    id: m.id,
                    role: m.role,
                    content: m.content,
                }));
            } else {
                this.state.messages = [];
            }
        } catch (e) {
            this.state.error = "Không tải được tin nhắn.";
        }
        this.scrollToBottom();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    async sendMessage() {
        const text = (this.state.inputText || "").trim();
        if (!text || this.state.isLoading) {
            return;
        }
        this.state.error = null;

        // Add user message locally.
        this.state.messages.push({
            _localId: this._nextLocalId(),
            role: "user",
            content: text,
        });
        this.state.inputText = "";
        this.state.isLoading = true;
        this.scrollToBottom();

        try {
            const res = await this.rpc("/ai_chatbot/send_message", {
                session_id: this.state.currentSessionId,
                message: text,
            });
            if (res && res.success) {
                if (res.session_id) {
                    this.state.currentSessionId = res.session_id;
                }
                this.state.messages.push({
                    _localId: this._nextLocalId(),
                    role: "assistant",
                    content: res.answer || "",
                });
                this.state.pendingAction = res.pending_action || null;
                await this.loadSessions();
            } else {
                this.state.error = (res && res.error) || "Đã có lỗi xảy ra.";
            }
        } catch (e) {
            this.state.error = "Lỗi kết nối tới máy chủ.";
        } finally {
            this.state.isLoading = false;
            this.scrollToBottom();
        }
    }

    async confirmAction() {
        if (!this.state.pendingAction) {
            return;
        }
        const actionId = this.state.pendingAction.id;
        this.state.isLoading = true;
        try {
            const res = await this.rpc("/ai_chatbot/confirm_action", {
                action_log_id: actionId,
            });
            if (res && res.success) {
                this.state.messages.push({
                    _localId: this._nextLocalId(),
                    role: "assistant",
                    content: res.message || "Đã thực hiện hành động.",
                });
                this.notification.add(res.message || "Đã thực hiện", { type: "success" });
                if (res.action) {
                    this.actionService.doAction(res.action);
                }
            } else {
                const msg = (res && res.error) || "Không thực hiện được hành động.";
                this.state.messages.push({
                    _localId: this._nextLocalId(),
                    role: "assistant",
                    content: "Lỗi: " + msg,
                });
                this.notification.add(msg, { type: "danger" });
            }
        } catch (e) {
            this.state.error = "Lỗi khi xác nhận hành động.";
        } finally {
            this.state.pendingAction = null;
            this.state.isLoading = false;
            this.scrollToBottom();
        }
    }

    async cancelAction() {
        if (!this.state.pendingAction) {
            return;
        }
        const actionId = this.state.pendingAction.id;
        try {
            await this.rpc("/ai_chatbot/cancel_action", { action_log_id: actionId });
            this.state.messages.push({
                _localId: this._nextLocalId(),
                role: "assistant",
                content: "Đã hủy hành động.",
            });
        } catch (e) {
            this.state.error = "Lỗi khi hủy hành động.";
        } finally {
            this.state.pendingAction = null;
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            const el = this.messagesRef.el;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        }, 50);
    }
}

AIChatbotClientAction.template = "cham_cong_ai_chatbot.AIChatbotClientAction";

registry.category("actions").add("ai_chatbot_client_action", AIChatbotClientAction);
