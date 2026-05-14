namespace SecureRiscVServer.Service.AES
{
    public static class AesCbc
    {
        public static byte[] Encrypt(byte[] data, byte[] key, byte[] iv)
        {
            var aes = new Aes128(key);
            data = Pad(data);

            byte[] result = new byte[data.Length];
            byte[] prev = iv;

            for (int i = 0; i < data.Length; i += 16)
            {
                byte[] block = data.Skip(i).Take(16).ToArray();
                for (int j = 0; j < 16; j++)
                    block[j] ^= prev[j];

                var enc = aes.EncryptBlock(block);
                Array.Copy(enc, 0, result, i, 16);
                prev = enc;
            }

            return result;
        }

        private static byte[] Pad(byte[] data)
        {
            int pad = 16 - data.Length % 16;
            return data.Concat(Enumerable.Repeat((byte)pad, pad)).ToArray();
        }

        private static byte[] Unpad(byte[] data)
        {
            int pad = data[^1];
            return data.Take(data.Length - pad).ToArray();
        }
    }
}
