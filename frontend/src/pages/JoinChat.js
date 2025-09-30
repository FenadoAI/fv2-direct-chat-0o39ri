import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, getAuthToken } from "../App";
import { MessageCircle, Loader } from "lucide-react";

const JoinChat = () => {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    joinChat();
  }, [token]);

  const joinChat = async () => {
    const authToken = getAuthToken();

    if (!authToken) {
      navigate(`/login?redirect=/invite/${token}`);
      return;
    }

    try {
      const response = await axios.post(
        `${API}/chats/join/${token}`,
        {},
        {
          headers: { Authorization: `Bearer ${authToken}` },
        }
      );

      // Successfully joined, redirect to chat
      setTimeout(() => {
        navigate(`/chat/${response.data.id}`);
      }, 1000);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to join chat");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 text-center">
        {loading && !error ? (
          <>
            <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageCircle className="w-8 h-8 text-indigo-600 animate-pulse" />
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              Joining Chat...
            </h1>
            <p className="text-gray-600">Please wait while we connect you</p>
            <div className="mt-6">
              <Loader className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
            </div>
          </>
        ) : error ? (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageCircle className="w-8 h-8 text-red-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              Unable to Join
            </h1>
            <p className="text-gray-600 mb-6">{error}</p>
            <button
              onClick={() => navigate("/")}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition"
            >
              Go to Dashboard
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
};

export default JoinChat;