# pubgkillloganalyzer

디스코드 분석 봇을 돌려서 실시간으로 게임의 킬로그를 분석해주는게 목표였으나
여러가지 문제점으로 더 이상 할꺼라면 다시 만들 필요가 있어보임

1. analyzeplayer 명령어의 속도가 너무 느리다.
   그리고 생각보다 json데이터의 크기가 엄청 크다.
   (몇번 다운받다 보면 100MB가 훌쩍 넘음)
   그러다 보니까 처리하는데 시간도 오래걸림

- 매치를 반복해서 다운로드 받는게 50 이 default인데 지금 사용하고 있는 서버 라즈베리파이4b 4gb 로는 30초씩 걸리는 경우도 있음

  원인 1. 파일 입출력을 사용해서 sd카드에 저장하기 때문에 속도가 메인 컴퓨터로 실행했을 때 보다 많이 느려짐
  해결방안-> 일부 빠른 속도가 필요한 데이터는 cache를 이용하면 상당히 빠름
  -> 하지만 라즈베리파이4b 메모리가 4gb밖에 안돼서 또 규모가 커지면 고려해야됨

  원인 2. 알고리즘에서 예외처리 함수를 기본적으로 여러번 호출하는 구조가 돼서 알고리즘이 느린 감이 좀 있음
  (ex isCanSavePlayerJson)

  예외처리 할 때 이걸 save 함수에 넣는게 아니라 그냥 완전 따로 만들어서 함수마다 예외처리를 처음에 해줘서
  한번만 연산하게 하는게 훨씬 나을듯

  지금은 뭐 복잡하게 가면 8번씩 연산하니까

2. pubg api 호출수가 생각보다 제한적이고 늘리기 위해서는 디스코드 봇 사용자 수를 증명하든가 해야 되는데
   지어 실시간으로 처리하려면  analyzeplayer를 킬로그가 하나 뜰 때마다 최악에는 2번씩 해야되는데
   429에러가 빈번하게 뜰 수 밖에 없음

4. 처음에 설계를 잘못해서 디렉토리 저장이 꼬여있음 (kakao / steam 중복 닉이 가능하기 때문에 나눠 줘야 함)

5. 파일이 존재하는지 찾는 함수 exist는 대소문자를 구별하지 않고
   open with으로 파일을 열면 대소문자를 구별하는데 지금 대소문자를 구별하는 알고리즘이 생각보다 너무 복잡함
   뭘 만들때마다 대소문자 처리를 해줘야하는데 어디서부터 처리해줘야 할지를 모르겠음

   현재 방식

   # 대소문자 구분없이 파일을 찾는 함수
def find_case_insensitive_path(dir_path, target_filename): 
    lowercase_target = target_filename.lower()
    for filename in os.listdir(dir_path):
        if filename.lower() == lowercase_target:
            return os.path.join(dir_path, filename)
    print("경고! 파일이 존재하지 않습니다.")
    return None

  def file_exists_case_sensitive(dir_path, target_filename):
    for filename in os.listdir(dir_path):
        if filename == target_filename:  
            return True
    return False

  이런식임

  무지성으로 만드는것부터 하면 확실히 망하는거 같음

  default_setting 이런거 하나 만들어서 기본적인 파일 디렉토리 이런것들 만들어주면 좋을듯? 

    

   
