using System.Collections.Concurrent;

namespace SecureRiscVServer.Data
{
    public class SessionStore
    {
        private readonly ConcurrentDictionary<string, SecureSession> _sessions = new();

        public void Set(string userId, SecureSession session)
            => _sessions[userId] = session;

        public SecureSession? Get(string userId)
            => _sessions.TryGetValue(userId, out var s) ? s : null;

        public void Remove(string userId)
            => _sessions.TryRemove(userId, out _);
    }
}
