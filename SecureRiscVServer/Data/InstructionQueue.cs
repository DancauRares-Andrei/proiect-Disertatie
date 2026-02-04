namespace SecureRiscVServer.Data
{
    public class InstructionQueue
    {
        private readonly Dictionary<string, Queue<uint>> _queues = new();

        public void Enqueue(string userId, IEnumerable<uint> instructions)
        {
            if (!_queues.ContainsKey(userId))
                _queues[userId] = new Queue<uint>();

            foreach (var i in instructions)
                _queues[userId].Enqueue(i);
        }

        public uint[] DequeueBatch(string userId, int max = 16)
        {
            if (!_queues.ContainsKey(userId))
                return Array.Empty<uint>();

            var q = _queues[userId];
            var list = new List<uint>();

            while (q.Count > 0 && list.Count < max)
                list.Add(q.Dequeue());

            return list.ToArray();
        }
    }

}
