import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API, getAuthToken, getUser, clearAuth, MY_HOMEPAGE_URL } from "../App";
import { MessageCircle, Plus, LogOut, Copy, Check } from "lucide-react";

const Dashboard = () => {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteLink, setInviteLink] = useState("");
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();
  const user = getUser();

  useEffect(() => {
    fetchChats();
  }, []);

  const fetchChats = async () => {
    try {
      const token = getAuthToken();
      const response = await axios.get(`${API}/chats/my-chats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setChats(response.data);
    } catch (err) {
      console.error("Error fetching chats:", err);
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      const token = getAuthToken();
      const response = await axios.post(
        `${API}/chats/create`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      const link = `${MY_HOMEPAGE_URL}/invite/${response.data.invite_token}`;
      setInviteLink(link);
      setShowInviteModal(true);
      fetchChats();
    } catch (err) {
      console.error("Error creating chat:", err);
    }
  };

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

  const copyInviteLink = () => {
    navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const openChat = (chatId) => {
    navigate(`/chat/${chatId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <MessageCircle className="w-8 h-8 text-indigo-600" />
              <h1 className="text-2xl font-bold text-gray-800">Chat App</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700 font-medium">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-800">Your Chats</h2>
          <button
            onClick={createNewChat}
            className="flex items-center space-x-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition shadow-md"
          >
            <Plus className="w-5 h-5" />
            <span>New Chat</span>
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-indigo-600 border-t-transparent"></div>
          </div>
        ) : chats.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
            <MessageCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              No chats yet
            </h3>
            <p className="text-gray-500 mb-6">
              Create a new chat and invite someone to start messaging
            </p>
            <button
              onClick={createNewChat}
              className="inline-flex items-center space-x-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition"
            >
              <Plus className="w-5 h-5" />
              <span>Create Your First Chat</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {chats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => openChat(chat.id)}
                className="bg-white rounded-xl shadow-md hover:shadow-xl transition cursor-pointer p-6 border border-gray-200"
              >
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                    <MessageCircle className="w-6 h-6 text-indigo-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800 text-lg">
                      {chat.other_user
                        ? `Chat with ${chat.other_user.username}`
                        : "Waiting for participant..."}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {chat.participants.length === 2
                        ? "Active conversation"
                        : "Share invite link to start"}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Chat Created!
            </h2>
            <p className="text-gray-600 mb-6">
              Share this link with someone to start chatting:
            </p>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 break-all">
              <code className="text-sm text-gray-700">{inviteLink}</code>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={copyInviteLink}
                className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition"
              >
                {copied ? (
                  <>
                    <Check className="w-5 h-5" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-5 h-5" />
                    <span>Copy Link</span>
                  </>
                )}
              </button>
              <button
                onClick={() => setShowInviteModal(false)}
                className="px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;