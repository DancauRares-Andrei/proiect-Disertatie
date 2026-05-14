using static SecureRiscVServer.Service.AES.AesTables;

namespace SecureRiscVServer.Service.AES
{
    public class Aes128
    {
        private readonly byte[] roundKeys;

        public Aes128(byte[] key)
        {
            if (key.Length != 16)
                throw new ArgumentException("Cheia AES-128 trebuie sa aiba 16 octeti");
            roundKeys = KeyExpansion(key);
        }

        public byte[] EncryptBlock(byte[] input)
        {
            byte[,] s = ToState(input);
            AddRoundKey(s, 0);

            for (int r = 1; r < 10; r++)
            {
                SubBytes(s);
                ShiftRows(s);
                MixColumns(s);
                AddRoundKey(s, r);
            }

            SubBytes(s);
            ShiftRows(s);
            AddRoundKey(s, 10);

            return FromState(s);
        }

        private static void SubBytes(byte[,] s)
        {
            for (int i = 0; i < 4; i++)
                for (int j = 0; j < 4; j++)
                    s[i, j] = SBox[s[i, j]];
        }

        private static void ShiftRows(byte[,] s)
        {
            for (int i = 1; i < 4; i++)
            {
                byte[] t = new byte[4];
                for (int j = 0; j < 4; j++)
                    t[j] = s[i, (j + i) % 4];
                for (int j = 0; j < 4; j++)
                    s[i, j] = t[j];
            }
        }

        private static void MixColumns(byte[,] s)
        {
            for (int c = 0; c < 4; c++)
            {
                byte a0 = s[0, c], a1 = s[1, c], a2 = s[2, c], a3 = s[3, c];
                s[0, c] = (byte)(GfMul(a0, 2) ^ GfMul(a1, 3) ^ a2 ^ a3);
                s[1, c] = (byte)(a0 ^ GfMul(a1, 2) ^ GfMul(a2, 3) ^ a3);
                s[2, c] = (byte)(a0 ^ a1 ^ GfMul(a2, 2) ^ GfMul(a3, 3));
                s[3, c] = (byte)(GfMul(a0, 3) ^ a1 ^ a2 ^ GfMul(a3, 2));
            }
        }

        private static byte GfMul(byte a, byte b)
        {
            byte p = 0;
            for (int i = 0; i < 8; i++)
            {
                if ((b & 1) != 0) p ^= a;
                bool hi = (a & 0x80) != 0;
                a <<= 1;
                if (hi) a ^= 0x1B;
                b >>= 1;
            }
            return p;
        }

        private static byte[] KeyExpansion(byte[] key)
        {
            byte[] w = new byte[176];
            Array.Copy(key, w, 16);

            int bytesGenerated = 16;
            int rconIter = 1;
            byte[] temp = new byte[4];

            while (bytesGenerated < 176)
            {
                Array.Copy(w, bytesGenerated - 4, temp, 0, 4);

                if (bytesGenerated % 16 == 0)
                {
                    RotWord(temp);
                    SubWord(temp);
                    temp[0] ^= Rcon[rconIter++];
                }

                for (int i = 0; i < 4; i++)
                {
                    w[bytesGenerated] = (byte)(w[bytesGenerated - 16] ^ temp[i]);
                    bytesGenerated++;
                }
            }
            return w;
        }

        private static void RotWord(byte[] w)
        {
            byte t = w[0];
            w[0] = w[1]; w[1] = w[2]; w[2] = w[3]; w[3] = t;
        }

        private static void SubWord(byte[] w)
        {
            for (int i = 0; i < 4; i++)
                w[i] = SBox[w[i]];
        }

        private void AddRoundKey(byte[,] s, int round)
        {
            for (int c = 0; c < 4; c++)
                for (int r = 0; r < 4; r++)
                    s[r, c] ^= roundKeys[round * 16 + c * 4 + r];
        }

        private static byte[,] ToState(byte[] input)
        {
            byte[,] s = new byte[4, 4];
            for (int i = 0; i < 16; i++)
                s[i % 4, i / 4] = input[i];
            return s;
        }

        private static byte[] FromState(byte[,] s)
        {
            byte[] outp = new byte[16];
            for (int i = 0; i < 16; i++)
                outp[i] = s[i % 4, i / 4];
            return outp;
        }
    }
}
